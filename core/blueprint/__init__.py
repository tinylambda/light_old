import typing
import logging
import copy
import time
import random
import string

from core.blueprint.exceptions import BlueprintException
from core.blueprint.exceptions import BlueprintTypeException


class Field:
    def __init__(
            self,
            verbose_name: typing.AnyStr = None,
            data_type: typing.Any = str,
            required: bool = True,
            default: typing.Any = None,
            multi: bool = False
    ):
        self.name: typing.AnyStr = None
        self.fullname: typing.AnyStr = None
        self.internal_name: typing.AnyStr = None
        self.verbose_name: typing.AnyStr = verbose_name
        self.data_type: typing.Any = data_type
        self.required: bool = required
        self.default: typing.Any = default
        self.multi: bool = multi

    def check_and_clean_if_possible(self, value) -> typing.Any:
        if self.multi:
            if not isinstance(value, list):
                raise BlueprintTypeException(f'{self.fullname} should be type of list')

            # return a new created list
            inner_list = []
            # check every item in the list
            for item in value:
                if not isinstance(item, self.data_type):
                    # try cast value type if data_type is not Blueprint and not None
                    # (may be int, str, bool, float...)
                    if not isinstance(self.data_type, BlueprintMeta):
                        try:
                            item = self.data_type(item) if item is not None else item
                            inner_list.append(item)
                        except ValueError as e:
                            raise BlueprintTypeException(
                                f'Cannot cast value {item} of list {self.fullname} <multi=True> to type {self.data_type}'
                            )
                    else:
                        # Do not try to cast value to blueprint!
                        raise BlueprintTypeException(
                            f'Every item of {self.fullname} should be type of {self.data_type}, but got {type(item)}'
                        )
                else:
                    inner_list.append(item)
            logging.debug(f'{self.fullname} type check passed!')
            return inner_list
        else:
            if isinstance(value, list):
                raise BlueprintTypeException(f'{self.fullname} should not be a list {value}')

            if not isinstance(value, self.data_type):
                # try cast value type if data_type is not Blueprint and not None
                # (may be int, str, bool...)
                if not isinstance(self.data_type, BlueprintMeta):
                    try:
                        value = self.data_type(value) if value is not None else value
                    except ValueError as e:
                        raise BlueprintTypeException(
                            f'Cannot cast value {value} of {self.fullname} to type {self.data_type}'
                        )
                else:
                    # Do not try to cast value to blueprint!
                    raise BlueprintTypeException(
                        f'{self.fullname} should be type {self.data_type}, but got {type(value)}'
                    )
            logging.debug(f'{self.fullname} type check passed!')
            return value

    def __get__(self, instance, owner):
        if instance is None:
            return self
        value = getattr(instance, self.internal_name, None)
        if value is None:
            if isinstance(self.default, (typing.MutableSequence, typing.MutableSet, typing.MutableMapping)):
                value = copy.copy(self.default)
            elif callable(self.default):
                value = self.default()
            else:
                value = self.default
        return value

    def __set__(self, instance, value):
        value = self.check_and_clean_if_possible(value)
        setattr(instance, self.internal_name, value)


class BlueprintMeta(type):
    def __new__(mcs, name: typing.AnyStr, bases: typing.Tuple, class_dict: typing.Dict):
        class_dict_copy = class_dict.copy()
        _id = Field(
            verbose_name='Instance ID',
            data_type=str,
            required=True,
            default=None,
        )
        _ts = Field(
            verbose_name='Timestamp',
            data_type=int,
            required=True,
            default=lambda: time.time(),
        )
        class_dict_copy.update({
            '_id': _id,
            '_ts': _ts,
        })

        # init all field instances
        for k, v in class_dict_copy.items():
            if isinstance(v, Field):
                v.name = k
                v.fullname = f'{name.lower()}.{k}'
                v.internal_name = f'field__{k}'

        meta_data: typing.Dict = {}
        meta_class = class_dict_copy.get('Meta')
        if meta_class:
            assert isinstance(meta_class, type)
            meta_class_dict = meta_class.__dict__
            for mk, mv in meta_class_dict.items():
                if not mk.startswith('__'):
                    meta_data.update({mk: mv})
        class_dict_copy.update({'meta_data': meta_data})

        def generate_id(self):
            return 'test'
        class_dict_copy.update({'generate_id': generate_id})

        def initialize_instance(self, init_data: typing.Dict):
            cls_dict: typing.Dict = self.__class__.__dict__
            for sk, sv in cls_dict.items():
                if isinstance(sv, Field):
                    if sk in init_data:
                        sk_v = init_data[sk]

                        data_type: typing.Any = sv.data_type
                        multi: bool = sv.multi

                        if multi:
                            assert isinstance(sk_v, list)
                            if isinstance(data_type, BlueprintMeta):
                                v_deserialized = []
                                for d in sk_v:
                                    # init every blueprint instance
                                    deserialized_instance = data_type(**d)
                                    # who is the parent of this blueprint ?
                                    deserialized_instance.parent = self
                                    v_deserialized.append(deserialized_instance)
                            else:
                                # Note: create new instance of list
                                v_deserialized = [item for item in sk_v]
                        else:
                            assert not isinstance(sk_v, list)
                            if isinstance(data_type, BlueprintMeta):
                                v_deserialized = data_type(**sk_v)
                                v_deserialized.parent = self
                            else:
                                v_deserialized = sk_v
                        # set attr value (through descriptor)
                        setattr(self, sk, v_deserialized)
                    else:
                        # default value for multi field should be []
                        if sv.multi and sv.default is None:
                            sv.default = []

                        # will get default value if any
                        sk_v = getattr(self, sk)
                        setattr(self, sk, sk_v)

            # generate id if needed
            if self.is_new:
                assert getattr(self, self.ID_NAME) is None
                id_template = self.meta_data.get('id_template')
                if id_template is None:
                    raise BlueprintTypeException(f'cannot generate id for new created blueprint '
                                                 f'because id_template not specified in Meta')
                context_render: typing.Dict = {
                    key: getattr(self, key)
                    for key in cls_dict
                    if isinstance(cls_dict[key], Field)
                }
                new_id = id_template.format(**context_render)
                setattr(self, self.ID_NAME, new_id)

            # check required value
            for sk, sv in cls_dict.items():
                if isinstance(sv, Field):
                    sk_v = getattr(self, sk, None)
                    if sk_v is None and sv.required and sv.default is None:
                        raise BlueprintTypeException(f'{sv.fullname} is required '
                                                     f'but no value provided and no default value set')

        def init(self, **kwargs):
            self.parent: typing.Any = None
            self.id_context: typing.Dict = {}
            self.is_new: bool = False
            if self.ID_NAME not in kwargs:
                self.is_new = True
            self.initialize_instance(kwargs)

        def serialize(self, selected_fields=None):
            if selected_fields is None:
                selected_fields = []
            else:
                selected_fields = list(selected_fields)
            cls_dict: typing.Dict = self.__class__.__dict__
            serialized: typing.Dict = {}

            if not self.should_serialize():
                return serialized
            else:
                for sk, sv in cls_dict.items():
                    if isinstance(sv, Field):
                        if selected_fields and sv.name not in selected_fields:
                            continue
                        sk_v = getattr(self, sk)

                        # serialize each field according to sv.data_type and sv.multi
                        data_type: typing.Any = sv.data_type
                        multi: bool = sv.multi
                        if multi:
                            # should serialize each item in the value
                            assert isinstance(sk_v, list)
                            if isinstance(data_type, BlueprintMeta):
                                serialized.update({
                                    sk: [item.serialize() for item in sk_v]
                                })
                            else:
                                serialized.update({
                                    sk: [item for item in sk_v]
                                })
                        else:
                            assert not isinstance(sk_v, list)
                            if isinstance(data_type, BlueprintMeta):
                                if sk_v.should_serialize():
                                    serialized.update({sk: sk_v.serialize()})
                            else:
                                serialized.update({sk: sk_v})
            return serialized

        class_dict_copy.update({
            'ID_NAME': '_id',
            'TS_NAME': '_ts',
            '__init__': init,
            'initialize_instance': initialize_instance,
            'serialize': serialize,
        })
        cls = type.__new__(mcs, name, bases, class_dict_copy)
        return cls


class Blueprint(metaclass=BlueprintMeta):
    def should_serialize(self):
        return True

    class Meta:
        id_template = ''
        is_top = False

