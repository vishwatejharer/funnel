import os

from flask import Response

from funnel.transports.base import TransportTransactionError
from funnel.transports.sms import SmsSender


class TestSmsSender:
    """
    Tests for SMS Sender
    """

    # Target Numbers (Test Only). See this
    # https://www.twilio.com/docs/iam/test-credentials
    TWILIO_CLEAN_TARGET = "+15005550010"
    TWILIO_INVALID_TARGET = "+15005550001"
    TWILIO_CANT_ROUTE = "+15005550002"
    TWILIO_NO_SMS_SERVICE = "+15005550009"

    # Dummy Message
    MESSAGE = "Test Message"

    def test_twilio_success(self):
        """
        Test if Message sending is a success.
        """
        sender = SmsSender(callback=False)
        sid = sender.send(self.TWILIO_CLEAN_TARGET, self.MESSAGE)
        assert sid

    def test_twilio_callback(self):
        """
        Test if Message sending is a success.
        """
        sender = SmsSender(callback=True)
        sid = sender.send(self.TWILIO_CLEAN_TARGET, self.MESSAGE)
        assert sid
        assert sender.twilio_callback is not None

    def test_twilio_failures(self):
        """
        Test if message sending is a failure
        """
        sender = SmsSender(callback=False)

        # Invalid Target
        try:
            sender.send(self.TWILIO_INVALID_TARGET, self.MESSAGE)
            assert False
        except TransportTransactionError:
            assert True

        # Cant route
        try:
            sender.send(self.TWILIO_CANT_ROUTE, self.MESSAGE)
            assert False
        except TransportTransactionError:
            assert True

        # No SMS Service
        try:
            sender.send(self.TWILIO_NO_SMS_SERVICE, self.MESSAGE)
            assert False
        except TransportTransactionError:
            assert True


class TestTwilioCallback:
    """
    Tests for Twilio SMS Callback
    """

    # Data Directory which contains JSON Files
    data_dir = os.path.join(os.path.dirname(__file__), 'data')

    # URL
    URL = 'api/1/sms/twilio_event'

    # Dummy headers. Or else tests will start failing
    HEADERS = {'X-Twilio-Signature': 'Random Signature'}

    def test_missing_header(self, test_client):
        """
        Check for Missing Twilio header and GET Methods.
        """

        # GET requests are not allowed.
        with test_client as c:
            resp: Response = c.get(self.URL)
        assert resp.status_code == 405

        # Missing Twilio headers
        with test_client as c:
            resp: Response = c.post(self.URL)
            data = resp.get_json()
        assert resp.status_code == 400
        assert data['status'] == 'error'

    def test_missing_json(self, test_client):
        """
        Test for Missing JSON Payload
        """
        with test_client as c:
            resp: Response = c.post(self.URL)
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['status'] == 'error'

    def test_bad_message(self, test_client):
        """
        Test for bad json message
        """
        with open(os.path.join(self.data_dir, "twilio_sms.json"), 'r') as file:
            data = file.read()
        with test_client as c:
            resp: Response = c.post(self.URL, json=data, headers=self.HEADERS)
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['status'] == 'error'