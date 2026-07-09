
import decimal
from datetime import datetime

import pytz
# from dictalchemy import DictableModel
from sqlalchemy.ext.declarative import declarative_base
from substrateinterface.utils.ss58 import ss58_encode


class BaseModelObj():

    serialize_exclude = None

    def save(self, session):
        session.add(self)
        session.flush()

    @property
    def serialize_type(self):
        return self.__class__.__name__.lower()

    def serialize_id(self):
        return self.id

    def serialize_formatting_hook(self, obj_dict):
        """ Hook to be able to process data before being serialized """
        return obj_dict

    def serialize(self, exclude=None):
        """ Serializes current models to a dict representation
        :param exclude: list of property names to exclude in serialization
        :returns: dict respresentation of current models
        """

        obj_dict = {
            'type': self.serialize_type,
            'id': self.serialize_id(),
            'attributes': {} #self.asdict(exclude=exclude or self.serialize_exclude)
        }

        obj_dict = self.serialize_formatting_hook(obj_dict)

        # Reformat certain data type
        for key, value in obj_dict['attributes'].items():
            if type(value) is datetime:
                obj_dict['attributes'][key] = value.replace(tzinfo=pytz.UTC).isoformat()

            if isinstance(value, decimal.Decimal):
                obj_dict['attributes'][key] = float(value)

        return obj_dict

    @classmethod
    def query(cls, session):
        return session.query(cls)

    def format_address(self, item):
        item['orig_value'] = item['value'].replace('0x', '')
        item['value'] = ss58_encode(item['value'].replace('0x', ''), 42)
        return item


BaseModel = declarative_base(cls=BaseModelObj)  ## type: BaseModelObj