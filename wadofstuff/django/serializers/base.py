"""
New base serializer class to handle full serialization of model objects.

Applied patch from http://code.google.com/p/wadofstuff/issues/detail?id=4
by stur...@gmail.com, Apr 7, 2009.
"""
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from django.core.serializers import base

class Serializer(base.Serializer):
    """Serializer for Django models inspired by Ruby on Rails serializer.

    """

    def __init__(self, *args, **kwargs):
        """Declare instance attributes."""
        self.options = None
        self.stream = None
        self.fields = None
        self.excludes = None
        self.relations = None
        self.extras = None
        self.use_natural_keys = None
        super(Serializer, self).__init__(*args, **kwargs)

    def serialize(self, queryset, **options):
        """Serialize a queryset with the following options allowed:
            fields - list of fields to be serialized. If not provided then all
                fields are serialized.
            excludes - list of fields to be excluded. Overrides ``fields``.
            relations - list of related fields to be fully serialized.
            extras - list of attributes and methods to include.
                Methods cannot take arguments.
        """
        self.options = options
        self.stream = options.pop("stream", StringIO())
        self.fields = options.pop("fields", [])
        self.excludes = options.pop("excludes", [])
        self.relations = options.pop("relations", [])
        self.extras = options.pop("extras", [])
        self.use_natural_keys = options.pop("use_natural_keys", False)

        self.start_serialization()
        for obj in queryset:
            self.start_object(obj)
            for field in obj._meta.local_fields:
                attname = field.attname
                if field.serialize:
                    if field.rel is None:
                        if attname not in self.excludes:
                            if not self.fields or attname in self.fields:
                                self.handle_field(obj, field)
                    else:
                        if attname[:-3] not in self.excludes:
                            if not self.fields or attname[:-3] in self.fields:
                                self.handle_fk_field(obj, field)
            for field in obj._meta.many_to_many:
                if field.serialize:
                    if field.attname not in self.excludes:
                        if not self.fields or field.attname in self.fields:
                            self.handle_m2m_field(obj, field)
            # relations patch
            if hasattr(obj._meta, 'get_all_related_objects'):
                related_fk_objects = obj._meta.get_all_related_objects()
            else:
                related_fk_objects = [
                    f for f in obj._meta.get_fields()
                    if (f.one_to_many or f.one_to_one) and
                    f.auto_created and
                    not f.concrete
                ]
            for ro in related_fk_objects:
                field_name = ro.get_accessor_name()
                if field_name not in self.excludes:
                    self.handle_related_fk_field(obj, field_name)

            if hasattr(obj._meta, 'get_all_related_many_to_many_objects'):
                related_m2m_objects = obj._meta.get_all_related_many_to_many_objects()
            else:
                related_m2m_objects = [
                    f for f in obj._meta.get_fields(include_hidden=True)
                    if f.many_to_many and f.auto_created
                ]

            for ro in related_m2m_objects:
                field_name = ro.get_accessor_name()
                if field_name not in self.excludes:
                    self.handle_related_m2m_field(obj, field_name)

            # end relations patch

            for extra in self.extras:
                self.handle_extra_field(obj, extra)
            self.end_object(obj)
        self.end_serialization()
        return self.getvalue()

    def handle_extra_field(self, obj, extra):
        """Called to handle 'extras' field serialization."""
        raise NotImplementedError

    # relations patch
    def handle_related_m2m_field(self, obj, field_name):
        """Called to handle 'reverse' m2m serialization."""
        raise NotImplementedError

    def handle_related_fk_field(self, obj, field_name):
        """Called to handle 'reverse' fk serialization."""
        raise NotImplementedError

