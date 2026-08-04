from pathlib import Path

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from rest_framework import serializers
from utils.custom_serializer_fields import CustomChoiceField
from eswatini.settings import EMAIL_FROM, WEBDOMAIN


# WEBDOMAIN is the frontend origin, so this is a Next.js page route — the app
# lives at /citizen-weather. Do not confuse it with the backend's
# /api/v1/weather/citizen-science/* API prefix.
CS_SIGN_IN_PATH = "/citizen-weather"


class EmailTypes:
    verification_email = "verification_email"
    forgot_password = "forgot_password"
    review_completed = "review_completed"
    review_overdue = "review_overdue"
    review_request = "review_request"
    new_user_password_setup = "new_user_password_setup"
    send_feedback = "send_feedback"
    cs_magic_link = "cs_magic_link"
    cs_reminder = "cs_reminder"

    FieldStr = {
        verification_email: "verification_email",
        forgot_password: "forgot_password",
        review_completed: "review_completed",
        review_overdue: "review_overdue",
        review_request: "review_request",
        new_user_password_setup: "new_user_password_setup",
        send_feedback: "send_feedback",
        cs_magic_link: "cs_magic_link",
        cs_reminder: "cs_reminder",
    }


class ListEmailTypeRequestSerializer(serializers.Serializer):
    type = CustomChoiceField(
        choices=list(EmailTypes.FieldStr.keys()), required=True
    )


def email_context(context: dict, type: str):
    if type == EmailTypes.new_user_password_setup:
        context.update(
            {
                "subject": "Welcome to Eswatini Drought Monitor",
                "body": """
                Welcome to Eswatini Drought Monitor platform!
                Before you can start exploring everything.
                Please set up your password using the link below:
                """,
                "cta_text": "Set Up My Password",
                "cta_url": "{0}/reset-password?code={1}".format(
                    WEBDOMAIN, context["reset_password_code"]
                ),
            }
        )
    if type == EmailTypes.verification_email:
        context.update(
            {
                "subject": "Verify Your Email Address",
                "body": """
                We're excited to have you on board. Before you can start
                exploring everything.
                Please click the link below to activate your account:
                """,
                "cta_text": "Verify My Email",
                "cta_url": "{0}/api/v1/email/verify?code={1}".format(
                    WEBDOMAIN, context["verification_code"]
                ),
            }
        )
    if type == EmailTypes.forgot_password:
        context.update(
            {
                "subject": "Reset Your Password",
                "body": """
                We received a password reset request for your account.
                If you did not make the request, please ignore this email.
                Otherwise, you can reset your password using the link below:
                """,
                "cta_text": "Reset My Password",
                "cta_url": "{0}/reset-password?code={1}".format(
                    WEBDOMAIN, context["reset_password_code"]
                ),
            }
        )
    if type == EmailTypes.review_completed:
        context.update(
            {
                "subject": (
                    "Review completed by "
                    "{0} for month {1}".format(
                        context["reviewer_name"],
                        context["year_month"],
                    )
                ),
                "body": (
                    """
                    Dear Admin,
                    {0} has completed the review of
                     the CDI Map for month <b>{1}</b>.
                    """.format(
                        context["reviewer_name"],
                        context["year_month"],
                    )
                ),
                "cta_text": "See the review",
                "cta_url": (
                    "{0}/publications/{1}/reviews/{2}".format(
                        WEBDOMAIN,
                        context["id"],
                        context["review_id"],
                    )
                ),
            }
        )
    if type == EmailTypes.review_overdue:
        context.update(
            {
                "subject": (
                    "We are awaiting for "
                    "you review of the CDI Map for month {0}".format(
                        context["year_month"],
                    )
                ),
                "body": (
                    """
                    Dear {0},
                    The {1} deadline for
                    the CDI Map review for month {2} has passed.
                    Please attend to the submit link below as soon as possible.
                    """.format(
                        context["name"],
                        context["due_date"],
                        context["year_month"],
                    )
                ),
                "cta_text": "Submit review",
                "cta_url": (
                    "{0}/reviews/{1}".format(
                        WEBDOMAIN,
                        context["id"],
                    )
                ),
            }
        )
    if type == EmailTypes.review_request:
        context.update(
            {
                "cta_text": "Submit Review",
                "cta_url": "{0}/reviews/{1}".format(
                    WEBDOMAIN,
                    context["id"],
                ),
            }
        )
    if type == EmailTypes.cs_magic_link:
        context.update(
            {
                "subject": "Sign in to Citizen Science Weather",
                "body": """
                Sanibonani {0},
                Welcome to Citizen Science Weather!
                Use the link below to open the monthly weather form for
                <b>{1}</b>. The link works for 7 days — you can request a
                fresh one anytime with just your email address.
                """.format(
                    context["name"],
                    context["station_name"],
                ),
                "cta_text": "Open my weather form",
                "cta_url": "{0}{1}?token={2}".format(
                    WEBDOMAIN, CS_SIGN_IN_PATH, context["token"]
                ),
            }
        )
    if type == EmailTypes.cs_reminder:
        context.update(
            {
                "subject": "Your {0} weather reading for {1} is due".format(
                    context["station_name"],
                    context["month_label"],
                ),
                "body": """
                Sanibonani {0},
                It's time to log last month's weather for <b>{1}</b>.
                You don't have to fill every field — whatever your station
                recorded is valuable. Siyabonga!
                """.format(
                    context["name"],
                    context["station_name"],
                ),
                "cta_text": "Submit my weather reading",
                "cta_url": "{0}{1}?token={2}".format(
                    WEBDOMAIN, CS_SIGN_IN_PATH, context["token"]
                ),
            }
        )
    if type == EmailTypes.send_feedback:
        context.update(
            {
                "subject": "Feedback from Eswatini Drought Monitor",
                "body": (
                    """
                    Dear Admin,
                    {0} has sent the following feedback:
                    <br>
                    {1}
                    """.format(
                        context["email"],
                        context["feedback"],
                    )
                ),
            }
        )
    return context


def send_email(
    context: dict,
    type: str,
    path=None,
    content_type=None,
    send=True,
):
    context = email_context(context=context, type=type)
    try:

        email_html_message = render_to_string("email/main.html", context)
        msg = EmailMultiAlternatives(
            "EDM - {0}".format(context.get("subject")),
            "Email plain text",
            EMAIL_FROM,
            context.get("send_to"),
        )
        msg.attach_alternative(email_html_message, "text/html")
        if path:
            msg.attach(Path(path).name, open(path).read(), content_type)
        if send:
            msg.send()
        if not send:
            return email_html_message
    except Exception as ex:
        print("Error", ex)
        print(ex)
