from flask import request

from twilio.request_validator import RequestValidator

from baseframe import statsd
from coaster.views import render_with

from .. import app
from ..models import SMS_STATUS, SMSMessage, db
from ..transports.sms import validate_exotel_token


@app.route('/api/1/sms/twilio_event', methods=['POST'])
@render_with(template=None, json=True)
def process_twilio_event():
    """Process SMS callback event from Twilio."""

    # Register the fact that we got a Twilio SMS event.
    # If there are too many rejects, then most likely a hack attempt.
    statsd.incr('phone_number.sms.twilio_event.received')

    # Check if we find twilio headers and if not reject it
    signature = request.headers.get('X-Twilio-Signature')
    if not signature:
        statsd.incr('phone_number.sms.twilio_event.rejected')
        return {'status': 'error', 'error': 'missing_signature'}, 422

    # Create Request Validator
    validator = RequestValidator(app.config['SMS_TWILIO_TOKEN'])
    if not validator.validate(
        request.url, request.form, request.headers.get('X-Twilio-Signature', '')
    ):
        statsd.incr('phone_number.sms.twilio_event.rejected')
        return {'status': 'error', 'error': 'invalid_signature'}, 422

    # FIXME: This code segment needs to change and re-written once Phone Number model is
    # in place.
    sms_message = SMSMessage.query.filter_by(
        transactionid=request.form['MessageSid']
    ).one_or_none()
    if sms_message is None:
        sms_message = SMSMessage(
            phone_number=request.form['To'],
            transactionid=request.form['MessageSid'],
            message=request.form['Body'],
        )
        db.session.add(sms_message)

    sms_message.status_at = db.func.utcnow()

    if request.form['MessageStatus'] == 'queued':
        sms_message.status = SMS_STATUS.QUEUED
    elif request.form['MessageStatus'] == 'failed':
        sms_message.status = SMS_STATUS.FAILED
    elif request.form['MessageStatus'] == 'delivered':
        sms_message.status = SMS_STATUS.DELIVERED
    elif request.form['MessageStatus'] == 'sent':
        sms_message.status = SMS_STATUS.PENDING
    else:
        sms_message.status = SMS_STATUS.UNKNOWN
    # Done
    db.session.commit()
    app.logger.info(
        "Twilio event for phone: %s %s",
        request.form['To'],
        request.form['MessageStatus'],
    )
    return {'status': 'ok', 'message': 'sms_notification_processed'}


@app.route('/api/1/sms/exotel_event/<secret_token>', methods=['POST'])
@render_with(template=None, json=True)
def process_exotel_event(secret_token: str):
    """Process SMS callback event from Exotel."""

    # Register the fact that we got a Exotel SMS event.
    # If there are too many rejects, then most likely a hack attempt.
    statsd.incr('phone_number.sms.exotel_event.received')

    # We just need to verify the token first.
    if not validate_exotel_token(secret_token):
        statsd.incr('phone_number.sms.exotel_event.rejected')
        return {'status': 'error', 'error': 'invalid_signature'}, 422

    # FIXME: This code segment needs to change and re-written once Phone Number model is
    # in place. The Message parameter has to be '' because exotel does not send back the
    # message as per the API model but the DB model expects it and we get a exception, if
    # we don't fix it.

    # There are only 3 parameters in the callback as per the documentation
    # https://developer.exotel.com/api/#send-sms
    # SmsSid - The Sid (unique id) of the SMS that you got in response to your request
    # To - Mobile number to which SMS was sent
    # Status - one of: queued, sending, submitted, sent, failed_dnd, failed
    sms_message = SMSMessage.query.filter_by(
        transactionid=request.form['SmsSid']
    ).one_or_none()
    if sms_message is None:
        sms_message = SMSMessage(
            phone_number=request.form['To'],
            transactionid=request.form['SmsSid'],
            message='',
        )
        db.session.add(sms_message)

    sms_message.status_at = db.func.utcnow()

    if request.form['Status'] == 'queued':
        sms_message.status = SMS_STATUS.QUEUED
    elif request.form['Status'] == 'failed' or request.form['Status'] == 'failed_dnd':
        sms_message.status = SMS_STATUS.FAILED
    elif request.form['Status'] == 'sent':
        sms_message.status = SMS_STATUS.DELIVERED
    elif request.form['Status'] == 'sending' or request.form['Status'] == 'submitted':
        sms_message.status = SMS_STATUS.PENDING
    else:
        sms_message.status = SMS_STATUS.UNKNOWN
    # Done
    db.session.commit()
    app.logger.info(
        "Exotel event for phone: %s %s",
        request.form['To'],
        request.form['Status'],
    )
    return {'status': 'ok', 'message': 'sms_notification_processed'}
