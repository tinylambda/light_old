from django.test import TestCase

from core.blueprint import Field
from core.blueprint import BlueprintMeta
from core.blueprint import Blueprint
from core.blueprint.exceptions import BlueprintTypeException


class BlueprintTestCase(TestCase):
    def setUp(self) -> None:
        class TestBlueprint(Blueprint):
            field = Field(
                verbose_name='Field Name',
                data_type=str,
                required=True,
                default='',
                multi=False
            )

            class Meta:
                id_template = '{_ts}'

        class TestBlueprintMutable(Blueprint):
            field = Field(
                verbose_name='Field Name',
                data_type=int,
                required=True,
                multi=True,
            )

            class Meta:
                id_template = '{_ts}'

        self.default_list = [1, 1, 1]

        class TestBlueprintMutableWithValues(Blueprint):
            field = Field(
                verbose_name='Field Name',
                data_type=int,
                required=True,
                default=self.default_list,
                multi=True,
            )

            class Meta:
                id_template = '{_ts}'

        class TestBlueprintMultiWithoutDefault(Blueprint):
            field = Field(
                verbose_name='Field Name',
                data_type=str,
                required=True,
                multi=True,
            )

            class Meta:
                id_template = '{_ts}'

        class TestBlueprintNested(Blueprint):
            field = Field(
                verbose_name='Field Name',
                data_type=TestBlueprintMutable,
                required=True,
                default=TestBlueprintMutable(),
                multi=False
            )

            class Meta:
                id_template = '{_ts}'

        class TestBlueprintRequiredField(Blueprint):
            field = Field(
                verbose_name='Field Name',
                data_type=str,
                required=True
            )

            class Meta:
                id_template = '{_ts}'

        self.TB_CLASS = TestBlueprint
        self.TB_CLASS_MUTABLE = TestBlueprintMutable
        self.TB_CLASS_MUTABLE_WITH_VALUES = TestBlueprintMutableWithValues
        self.TB_CLASS_MULTI_NO_DEFAULT = TestBlueprintMultiWithoutDefault
        self.TB_CLASS_NESTED = TestBlueprintNested
        self.TB_CLASS_REQUIRED_FIELD = TestBlueprintRequiredField

    def test_blueprint_field_operation(self):
        tb = self.TB_CLASS()
        self.assertEqual(self.TB_CLASS.field.name, 'field', 'error set field name')
        self.assertEqual(self.TB_CLASS.field.internal_name, 'field__field', 'error internal name')
        self.assertEqual(self.TB_CLASS.field.fullname, f'{self.TB_CLASS.__name__.lower()}.field', 'error set fullname')

        # default value works ?
        self.assertEqual(tb.field, '', 'default value not works')
        self.assertTrue(
            hasattr(tb, self.TB_CLASS.field.internal_name),
            'should has internal_name after init'
        )

        tb.field = 'hello'
        self.assert_(
            hasattr(tb, self.TB_CLASS.field.internal_name),
            'internal_name not created'
        )
        self.assertEqual(tb.field, 'hello', 'assignment not works')
        self.assertEqual(
            getattr(tb, self.TB_CLASS.field.internal_name),
            'hello',
            'value of internal_name wrong'
        )

        tb = self.TB_CLASS(field='hello')

    def test_blueprint_mutable_field(self):
        instance_1 = self.TB_CLASS_MUTABLE()
        instance_2 = self.TB_CLASS_MUTABLE()
        self.assertEqual(
            self.TB_CLASS_MUTABLE.field.default, [],
            'default value not correct'
        )
        self.assertEqual(
            instance_1.field, self.TB_CLASS_MUTABLE.field.default, 'default value not works'
        )
        self.assertEqual(
            instance_2.field, self.TB_CLASS_MUTABLE.field.default, 'default value not works'
        )
        self.assertEqual(
            instance_1.field, instance_2.field, 'default value should be equal'
        )
        self.assertIsNot(
            instance_1.field, instance_2.field, 'should have two different instances'
        )

        tb = self.TB_CLASS_MUTABLE_WITH_VALUES()
        self.assertEqual(
            getattr(tb, 'field'), [1, 1, 1],
            'default value does not work'
        )
        self.assertIsNot(
            getattr(tb, 'field'), self.default_list,
            'should not refer to the same instance'
        )

    def test_blueprint_multi_set_default_automatically(self):
        tb = self.TB_CLASS_MULTI_NO_DEFAULT()
        self.assertEqual(
            tb.field, [], 'multi should imply default value []'
        )

    def test_blueprint_type_info(self):
        self.assertIsInstance(self.TB_CLASS, BlueprintMeta, 'type info error')
        self.assertIsInstance(Blueprint, BlueprintMeta, 'type info error')
        self.assertTrue(issubclass(self.TB_CLASS, Blueprint), 'type info error')

    def test_blueprint_assignment_protect(self):
        tb = self.TB_CLASS_NESTED()

        def f(v, k='field'):
            setattr(tb, k, v)

        # int cannot be casted to blueprint
        self.assertRaises(
            BlueprintTypeException,
            f, 100
        )
        # str cannot be casted to blueprint
        self.assertRaises(
            BlueprintTypeException,
            f, 'hello'
        )

        tb = self.TB_CLASS()
        # int can be casted to str
        tb.field = 100
        # str OK
        tb.field = 'hello'

        # list of int
        tb = self.TB_CLASS_MUTABLE()
        self.assertRaises(
            BlueprintTypeException,
            # 'hello' cannot be casted to int
            f, [100, 'hello']
        )
        # can be cast to int
        f(['100', 200, 300])

        # init in __init__, implicit cast
        tb = self.TB_CLASS(field=100)
        self.assertEqual(
            tb.field, '100', 'init failed'
        )

        # _ts should be cast to int
        self.assertIsInstance(
            getattr(tb, '_ts'), int
        )

        # set do value cast, so _ts becomes 9 as int
        setattr(tb, '_ts', 9.776)
        self.assertEqual(
            getattr(tb, '_ts'), 9, 'value type cast error'
        )

        # can cast 9.776 from int to str
        tb.field = 9.776

        # can not cast '9.776' from string to int
        self.assertRaises(
            BlueprintTypeException,
            f, '9.776', k='_ts'
        )

    def test_blueprint_id_generate(self):
        tb = self.TB_CLASS()
        # we use '{_ts}' as id_template
        self.assertEqual(
            getattr(tb, '_id'), str(getattr(tb, '_ts'))
        )

    def test_blueprint_required_field(self):
        # lack required field should raise BlueprintTypeException
        with self.assertRaises(BlueprintTypeException):
            self.TB_CLASS_REQUIRED_FIELD()


