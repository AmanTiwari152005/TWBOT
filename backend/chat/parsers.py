import json

from rest_framework.exceptions import ParseError
from rest_framework.parsers import BaseParser


class PlainTextJSONParser(BaseParser):
    media_type = 'text/plain'

    def parse(self, stream, media_type=None, parser_context=None):
        raw_body = stream.read().decode('utf-8').strip()

        if not raw_body:
            return {}

        try:
            return json.loads(raw_body)
        except ValueError as error:
            raise ParseError('Malformed JSON in text/plain request.') from error
