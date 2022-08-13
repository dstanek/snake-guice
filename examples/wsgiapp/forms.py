from formencode import Schema
from formencode.validators import Email, String


class MyForm(Schema):
    allow_extra_fields = True

    name = String(not_empty=True)
    email = Email(not_empty=True)
