
from firebase_admin import messaging

def send_notification(token, title, body):
    message = messaging.Message(
        notification=messaging.Notification(
            title=title,
            body=body
        ),
        token=token
    )

    response = messaging.send(message)
    return response


def send_bulk_notification(tokens, title, body):

    messages = [
        messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            token=token
        )
        for token in tokens
    ]

    response = messaging.send_each(messages)

    return {
        "success_count": response.success_count,
        "failure_count": response.failure_count
    }

def send_order_notification(tokens, title, body, order_id):

    messages = [
        messaging.Message(
            # notification=messaging.Notification(
            #     title=title,
            #     body=body
            # ),
            data={
                "title": title,
                "body": body,
                "type": "Order Created",
                "order_id": str(order_id)
            },
            token=token
        )
        for token in tokens
    ]

    response = messaging.send_each(messages)

    print("Success:", response.success_count)
    print("Failure:", response.failure_count)

    return response