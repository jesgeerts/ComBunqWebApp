from django.contrib.sessions.backends.db import SessionStore
from django.contrib.sessions.models import Session
# from django.core.exceptions import ObjectDoesNotExist
from apiwrapper.clients.api_client import ApiClient as API
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import json
import time
from filecreator.creator import Creator
# from pprint import pprint
from django.core import signing
import datetime
import base64


class callback:
    """docstring for session.
        This class handles the callbacks to the bunq api.

        user_file = the contents of the users ecnrypted json.
        api_token = the api token from the bunq app.
        user = is the currently logged in user.
        init_api = is the API instance before session token
        userID = is the provided user id that can be used to retrieve data
                 of a specific user register to the API key.
        accountID = cardID = id's to retrieve a specific card or account
                    belonging to the user id.
        account_url = url used by most endpoints
        s = is the server session token stored in the django session. The key
            for this session is sotred in the database, only logged in users
            can retreive their keys.
        bunq_api = is the API instace after the session token
                   is retrieved.
    """

    __variables = ['user_id', 'account_id', 'payment_id', 'date_start',
                   'date_end', 'statement_format', 'regional_format',
                   'api_key']

    def __init__(self, user, decrypt=True, **kwargs):
        self._kwargs_setter(kwargs)
        self._user = user
        self._use_session_token = True

        if decrypt:
            self._get_user_data()

    def _kwargs_setter(self, kwargs):
        for k in self.__variables:
            if kwargs.get(k) is not None:
                setattr(self, k, kwargs.get(k))
            else:
                setattr(self, k, None)

    def _get_user_data(self):
        session_key = self._user.session.session_token
        enc_string = Session.objects.get(
            session_key=session_key).get_decoded()['api_data']
        dec_data = signing.loads(enc_string)
        self.bunq_api = dec_data

    def installation(self):
        self._use_session_token = False
        rsa_key = self.create_rsa_key()
        bunq_api = API(privkey=rsa_key)

        r = bunq_api.endpoints.installation.create_installation()

        if r.status_code == 200:
            token = r.json()['Response'][1]['Token']['token']
            server_pubkey = r.json()['Response'][2]['ServerPublicKey'][
                                            'server_public_key']

            data = {
                'token': token,
                'server_pubkey': server_pubkey,
                'private_key': rsa_key,
                'api_key': self.api_key
            }

            self.bunq_api = data
            registration = self.register()

            if self.check_status_code(registration):
                return {
                    'data': data,
                    'status': True
                }
            else:  # pragma: no cover
                return {'status': False}

        else:  # pargma: no cover
            error = {
                'Error': [{
                    'error_description_translated': ('something went wrong'
                                                     ' during installation')
                }]
            }
            return error

    def register(self):
        '''
        Registers the device
        https://doc.bunq.com/api/1/call/device-server/method/post
        '''
        self._use_session_token = False
        r = self.bunq_api.endpoints.device_server \
                                   .create_new_device_server('ComBunqWebApp')
        return r

    def load_file(self):
        start_session = self.start_session()

        if 'Response' in start_session:
            self.user_id = self._get_user_id(start_session['Response'])
            start_session = start_session['Response']

        else:  # pragma: no cover
            return start_session

        time.sleep(1.5)

        accounts = self.accounts()

        time.sleep(.5)

        self.account_id = accounts['Response'][0][
                                            'MonetaryAccountBank']['id']

        time.sleep(1.5)

        payments = self.payment()

        response = {
            'start_session': start_session,
            'accounts': accounts['Response'],
            'payments': payments['Response']
        }

        return response

    def start_session(self):
        '''
        Starts a server-session according to
        https://doc.bunq.com/api/1/call/session-server/method/post
        the response can also be seen via this link on the docs. This session
        token is needed to make future API calls to the API. Therefore its
        getting stored in the database in the user session.

        From the docs:
        A session expires after the same amount of time you have set for auto
        logout in your user account. If a request is made 30 seconds before a
        session expires, it will automatically be extended.

        When the session expires the token will be unusbale.
        '''
        if self._check_session_active():
            Creator(self._user).create_avatar_from_session()
            return self._get_saved_response(name='start_session')

        self._use_session_token = False

        r = self.bunq_api.endpoints.session_server.create_new_session_server()

        self._use_session_token = True

        if self.check_status_code(r):
                session_token = r.json()['Response'][1]['Token']['token']
                user_id = self._get_user_id(r.json()['Response'])
                avatar_uuid = self.get_avatar_id(r.json()['Response'],
                                                 'start_session')
                session_id = r.json()['Response'][0]['Id']['id']

                self._store_session_server_info(session_token, user_id,
                                                session_id)

                self.get_avatar(avatar_uuid)

                self._sotre_session_expire(r.json()['Response'][2])

                self._save_response(response=r.json(), name='start_session')
                return r.json()
        else:  # pragma: no cover
            error = {
                'Error': [{
                    'error_description_translated': ('Something went wrong'
                                                     ' starting the session')
                }]
            }
            return error

    def delete_session(self):
        session_id = self._user.session.session_server_id
        r = self.bunq_api.endpoints.session.delete_session(int(session_id))

        if self.check_status_code(r):
            return True
        else:  # pragma: no cover
            return False

    def users(self):
        '''
        Returns a list of all the users belonging to this API key.
        https://doc.bunq.com/api/1/call/user/
        If an id is given then the info of that specific user is retrieved.
        '''

        if self.user_id is None:
            r = self.bunq_api.endpoints.user.get_logged_in_user()
        else:
            r = self.bunq_api.endpoints.user.get_user_by_id(self.user_id)

        if 'Response' in r.json():
            avatar_id = self.get_avatar_id(r.json()['Response'])
            self.get_avatar(avatar_id)
        return r.json()

    def accounts(self):
        '''
        Returns a list of all accounts:
        https://doc.bunq.com/api/1/call/monetary-account/
        When usign a GET method a specific account can be returned.
        '''

        if self.account_id is not None:
            r = self.bunq_api.endpoints.monetary_account.get_account_by_id(
                self.user_id, self.account_id).json()
        else:
            r = self.bunq_api.endpoints.monetary_account \
                                       .get_all_accounts_for_user(
                                                                self.user_id
                                                                    ).json()
        return r

    def payment(self, mode='normal'):
        '''
        Returns a list of all transactions from an account. If an payment id is
        given then a specific transaction will be returned.

        Via this callback payments can be made aswell.

        https://doc.bunq.com/api/1/call/payment
        '''
        if mode == 'normal':
            if self.account_id and self.user_id is not None:
                if self.payment_id is None:
                    r = self.bunq_api.endpoints\
                            .payment.get_all_payments_for_account(
                                                        self.user_id,
                                                        self.account_id).json()
                else:
                    r = self.bunq_api.endpoints.payment.get_payment_by_id(
                        self.user_id, self.account_id, self.payment_id
                    ).json()
            else:
                r = {
                    'Error': [{
                        'error_description_translated': ('account or userd id '
                                                         'is not specified')
                    }]
                }
            return r

    def card(self):
        '''
        Return all the cards available to the user. Or a specific card if a
        cardID is given
        '''

        if self.account_id and self.user_id is not None:
            r = self.bunq_api.endpoints.card.get_card_for_user_by_id(
                self.user_id, self.account_id).json()
        elif self.account_id is None and self.user_id is not None:
            r = self.bunq_api.endpoints.card.get_all_cards_for_user(
                self.user_id
            ).json()
        else:  # pragma: no cover
            r = {
                'Error': [{
                    'error_description_translated': 'user_id must be specified'
                }]
            }
        return r

    def invoice(self):
        '''
        Returns the invoice of the user
        '''
        if self.user_id is not None:
            r = self.bunq_api.endpoints.invoice.get_all_invoices_for_user(
                self.user_id
            )

            if self.check_status_code(r):
                try:
                    invoice = r.json()['Response'][0]['Invoice']
                except IndexError:  # pragma: no cover
                    error = {
                        'Error': [{
                            'error_description_translated': ('the response '
                                                             'seems'
                                                             'to have no '
                                                             'invoice '
                                                             'in it.')
                        }]
                    }
                    return error
                else:
                    # return self.get_invoice_pdf(json.dumps(invoice))
                    creator = Creator(user=self._user, extension=None)
                    data = json.dumps(invoice)
                    return creator.invoice(data)
            else:  # pragma: no cover
                return r.json()

        else:  # pragma: no cover
            error = {
                'Error': [{
                    'error_description_translated': ('There is no user id'
                                                     'specified')
                }]
            }
            return error

    def get_payment_pdf(self):
        if self.payment_id is not None:
            payment = self.payment()

            try:
                pdf = Creator(self._user,
                              'pdf').payment(payment['Response'][0],
                                             transaction_id=self.payment_id)
            except KeyError:  # pragma: no cover
                error_msg = payment['Error'][0]['error_description_translated']
                error = {
                    'Error': [{
                        'error_description_translated': ('There seems to be'
                                                         ' an error with the'
                                                         ' response.'
                                                         '\n'
                                                         '%s' % error_msg
                                                         )
                    }]}
                return error
            return pdf
        else:  # pragma: no cover
            error = {
                'Error': [{
                    'error_description_translated': 'Payment id is not set'
                }]
            }

            return error

    def get_avatar(self, avatar_id):
        r = self.bunq_api.endpoints \
                .attachment_public.get_content_of_public_attachment(avatar_id)
        enc_png = base64.b64encode(r.content)
        self._save_response(enc_png.decode(), 'avatar')

        Creator(self._user).create_avatar_from_session()

    def customer_statement(self):
        if self.statement_format == 'PDF':
            r = self.bunq_api.endpoints.customer_statement \
                                       .create_customer_statement_pdf(
                                                            self.user_id,
                                                            self.account_id,
                                                            self.date_start,
                                                            self.date_end,
                                                            )
            extension = '.pdf'
        elif self.statement_format == 'CSV':
            r = self.bunq_api.endpoints \
                             .customer_statement \
                             .create_customer_statement_csv(self.user_id,
                                                            self.account_id,
                                                            self.date_start,
                                                            self.date_end,
                                                            )
            extension = '.csv'
        elif self.statement_format == 'MT940':
            r = self.bunq_api.endpoints \
                             .customer_statement \
                             .create_customer_statement_mt940(self.user_id,
                                                              self.account_id,
                                                              self.date_start,
                                                              self.date_end)
            extension = '.mt940'
        else:  # pragma: no cover
            error = {
                'Error': [{
                    'error_description_translated': ('statement_format not'
                                                     ' not set correctly.')
                }]
            }
            return error
        if self.check_status_code(r):
            statement_id = r.json()['Response'][0]['Id']['id']
            return self.get_content_of_customer_statement(statement_id,
                                                          extension)
        else:  # pragma: no cover
            return r.json()

    def get_content_of_customer_statement(self, statement_id, extension):
        r = self.bunq_api.endpoints \
                         .customer_statement \
                         .get_content_of_customer_statement(self.user_id,
                                                            self.account_id,
                                                            statement_id)
        if self.check_status_code(r):
            creator = Creator(self._user)
            temp_file = creator.temp_file(extension=extension)
            temp_file.write(r.content)
            temp_file.close()
            creator.store_in_session(file_path=temp_file.name)

            response = {
                'Resopnse': [{
                    'status': 'Statement has been created'
                }]
            }
            return response
        else:  # pragma: no cover
            return r.json()

    def _check_session_active(self):
        current_time = datetime.datetime.now(datetime.timezone.utc)
        session_end = self._user.session.session_end_date

        if current_time >= session_end:
            return False
        else:
            return True

    def _store_session_server_info(self, session_token, user_id, session_id):
        s = SessionStore()
        s['user_id'] = user_id
        s.create()
        self._user.session \
                  .session_user_id = s.session_key

        self._user.session.session_server_id = session_id
        self._user.session.session_server_token = session_token
        self._user.save()

    def _sotre_session_expire(self, response):
        try:
            response = response['UserCompany']
        except KeyError:  # pragma: no cover
            response = response['UserPerson']
        finally:
            session_timeout = datetime.timedelta(seconds=response[
                                                            'session_timeout'])
            session_expire_date = datetime.datetime.now(
                datetime.timezone.utc
            ) + session_timeout

            self._user.session.session_end_date = session_expire_date
            self._user.save()

    def _save_response(self, response, name):
        session_key = self._user.session.session_token
        s = SessionStore(session_key=session_key)
        enc_data = signing.dumps(obj=response)
        s[name] = enc_data
        s.save()

    def _get_saved_response(self, name):
        session_key = self._user.session.session_token
        s = SessionStore(session_key=session_key)
        dec_data = signing.loads(s[name])
        return dec_data

    @property
    def bunq_api(self):
        if self.session_server_token is not None and self._use_session_token:
            self._bunq_api.session_token = self.session_server_token
            return self._bunq_api
        else:
            return self._bunq_api

    @bunq_api.setter
    def bunq_api(self, value):
        api = API(privkey=value['private_key'], api_key=value['api_key'],
                  installation_token=value['token'],
                  server_pubkey=value['server_pubkey'])
        self._bunq_api = api

    @property
    def session_server_token(self):
        session_server_token = self._user.session.session_server_token
        return session_server_token

    @property
    def user_id(self):
        if self._user_id is None or self._user_id is '':
            return None
        else:
            return self.to_int(self._user_id)

    @user_id.setter
    def user_id(self, value):
        self._user_id = value

    @property
    def account_id(self):
        if self._account_id is None or self._account_id is '':
            return None
        else:
            return self.to_int(self._account_id)

    @account_id.setter
    def account_id(self, value):
        self._account_id = value

    @property
    def payment_id(self):
        if self._payment_id is None or self._payment_id is '':
            return None
        else:
            return self.to_int(self._payment_id)

    @payment_id.setter
    def payment_id(self, value):
        self._payment_id = value

    @property
    def date_start(self):
        if self._date_start is None:  # pragma: no cover
            return None
        else:
            return self._date_start

    @date_start.setter
    def date_start(self, value):
        self._date_start = value

    @property
    def date_end(self):
        if self._date_end is None:  # pragma: no cover
            return None
        else:
            return self._date_end

    @date_end.setter
    def date_end(self, value):
        self._date_end = value

    @property
    def statement_format(self):
        if self._statement_format is None:  # pragma: no cover
            return None
        else:
            return self._statement_format

    @statement_format.setter
    def statement_format(self, value):
        self._statement_format = value

    @property
    def regional_format(self):  # pragma: no cover
        if self._regional_format is None:
            return None
        else:
            return self._regional_format

    @regional_format.setter
    def regional_format(self, value):
        self._regional_format = value

    @property
    def api_key(self):
        if self._api_key is None:  # pragma: no cover
            return None
        else:
            return self._api_key

    @api_key.setter
    def api_key(self, value):
        self._api_key = value

    @staticmethod
    def to_int(string):
        return int(string)

    @staticmethod
    def get_avatar_id(response, mode=None):
        if mode == 'start_session':
            try:
                id = response[2]['UserCompany']['avatar']['image'][0][
                                                    'attachment_public_uuid']
            except KeyError:  # pragma: no cover
                id = response[2]['UserPerson']['avatar']['image'][0][
                                                    'attachment_public_uuid']
            return id
        else:
            try:
                id = response[0]['UserCompany']['avatar']['image'][0][
                                                    'attachment_public_uuid']
            except KeyError:  # pragma: no cover
                id = response[0]['UserPerson']['avatar']['image'][0][
                                                    'attachment_public_uuid']
            return id

    @staticmethod
    def _get_user_id(response):
        try:
            id = response[2]['UserCompany']['id']
        except KeyError:  # pragma: no cover
            id = response[2]['UserPerson']['id']

        return id

    @staticmethod
    def check_status_code(response):
        if response.status_code == 200:
            return True
        else:  # pragma: no cover
            return False

    @staticmethod
    def create_rsa_key():
        # generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )

        # output PEM encoded version of private key
        privateKey = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )

        return privateKey.decode()
