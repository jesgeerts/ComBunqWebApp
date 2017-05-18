from apiwrapper.endpoints.endpoint import Endpoint
from apiwrapper.endpoints.user import User


class Card(Endpoint):

    __endpoint_card = "card"

    @classmethod
    def _get_base_endpoint(cls, user_id, card_id=None):
        endpoint = User._get_base_endpoint(user_id)
        endpoint += "/%s" % cls.__endpoint_card
        if card_id is not None:
            endpoint += "/%d" % card_id
        return endpoint

    def get_all_cards_for_user(self, user_id):
        endpoint = self._get_base_endpoint(user_id)

        return self._make_get_request(endpoint)

    def get_card_for_user_by_id(self, user_id, card_id):
        endpoint = self._get_base_endpoint(user_id, card_id)

        return self._make_get_request(endpoint)
