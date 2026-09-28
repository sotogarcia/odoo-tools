###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################


from operator import eq, ge, gt, le, lt, ne
from re import sub

from odoo.exceptions import ValidationError
from odoo.osv.expression import AND, FALSE_DOMAIN, TRUE_DOMAIN
from odoo.tools import SQL
from odoo.tools.safe_eval import safe_eval
from odoo.tools.translate import _, _lt

INVALID_DOMAIN = _lt("Given domain expression %r is not a valid ORM domain")
INVALID_CTX = _lt("Given context expression %r is not a valid context mapping")

OPERATOR_MAP = {
    "=": eq,
    "!=": ne,
    "<": lt,
    "<=": le,
    ">": gt,
    ">=": ge,
}


def evaluate_domain(recordset, src_domain, default=None, raise_on_fail=True):
    """Evaluate a field domain definition into a valid ORM domain.

    The source domain can be provided as a list, tuple, string expression,
    callable, or ``None``. Lists and tuples are used directly after conversion
    to a list. Callables receive ``recordset`` as their only argument.

    String expressions are evaluated with ``safe_eval`` using a generic Odoo
    evaluation context. The following variables are explicitly available:

        ``uid``
            ID of the current Odoo user.

        ``user``
            Current ``res.users`` record.

        ``context``
            Current Odoo environment context.

    Context-specific values such as ``active_id``, ``active_ids`` or custom
    keys are intentionally not exposed as independent variables. They remain
    available through the ``context`` mapping, for example
    ``context.get("active_id")``. This keeps the helper independent from more
    specialized evaluation environments such as ``ir.actions``.

    Args:
        recordset (odoo.models.Model): Recordset used to provide the Odoo
            environment and passed to callable domain definitions.
        src_domain (list | tuple | str | callable | None): Domain definition to
            evaluate. Lists and tuples are converted to a list, strings are
            evaluated with ``safe_eval``, callables are invoked with
            ``recordset``, and ``None`` leaves the default value unchanged.
        default (list | tuple | None, optional): Fallback value returned when
            the domain cannot be evaluated and ``raise_on_fail`` is False.
            Defaults to None.
        raise_on_fail (bool, optional): If True, raise an exception when the
            domain cannot be evaluated or does not produce a list or tuple.
            If False, return ``default`` instead. Defaults to True.

    Returns:
        list | tuple | None: Evaluated ORM domain. If evaluation fails and
        ``raise_on_fail`` is False, returns ``default``.

    Raises:
        ValueError: If evaluation of a string or callable domain fails and
            ``raise_on_fail`` is True.
        TypeError: If ``src_domain`` has an unsupported type, or if the
            evaluated result is not a list or tuple, and ``raise_on_fail`` is
            True.
    """
    domain = default

    if isinstance(src_domain, (list, tuple)):
        domain = list(src_domain)

    elif isinstance(src_domain, str):
        eval_context = {
            "uid": recordset.env.uid,
            "user": recordset.env.user,
            "context": recordset.env.context,
        }

        try:
            domain = safe_eval(src_domain, eval_context)
        except Exception as ex:
            if raise_on_fail:
                raise ValueError(INVALID_DOMAIN % src_domain) from ex

            domain = default

    elif callable(src_domain):
        try:
            domain = src_domain(recordset)
        except Exception as ex:
            if raise_on_fail:
                raise ValueError(INVALID_DOMAIN % src_domain) from ex

            domain = default

    elif src_domain is not None and raise_on_fail:
        raise TypeError(INVALID_DOMAIN % src_domain)

    if domain is not None and not isinstance(domain, (list, tuple)):
        if raise_on_fail:
            raise TypeError(INVALID_DOMAIN % src_domain)

        domain = default

    return domain


def evaluate_context(recordset, src_context, default=None, raise_on_fail=True):
    """Evaluate a field context definition into a valid context mapping.

    The source context can be provided as a dictionary, a string expression,
    callable, or ``None``. String expressions are evaluated with ``safe_eval``
    using a minimal evaluation context containing the current Odoo environment
    context. Callables receive ``recordset`` as their only argument.

    Args:
        recordset (odoo.models.Model): Recordset used to provide the Odoo
            environment and passed to callable context definitions.
        src_context (dict | str | callable | None): Context definition to
            evaluate. Dictionaries are used directly, strings are evaluated
            with ``safe_eval``, callables are invoked with ``recordset``, and
            ``None`` leaves the default value unchanged.
        default (dict | None, optional): Fallback value returned when the
            context cannot be evaluated and ``raise_on_fail`` is False.
            Defaults to None.
        raise_on_fail (bool, optional): If True, raise an exception when the
            context cannot be evaluated or does not produce a dictionary. If
            False, return ``default`` instead. Defaults to True.

    Returns:
        dict | None: Evaluated context mapping. If evaluation fails and
        ``raise_on_fail`` is False, returns ``default``.

    Raises:
        ValueError: If evaluation of a string or callable context fails and
            ``raise_on_fail`` is True.
        TypeError: If ``src_context`` has an unsupported type, or if the
            evaluated result is not a dictionary, and ``raise_on_fail`` is
            True.
    """
    context = default

    if isinstance(src_context, dict):
        context = src_context

    elif isinstance(src_context, str):
        eval_context = {
            "context": recordset.env.context,
        }

        try:
            context = safe_eval(src_context, eval_context)
        except Exception as ex:
            if raise_on_fail:
                raise ValueError(INVALID_CTX % src_context) from ex

            context = default

    elif callable(src_context):
        try:
            context = src_context(recordset)
        except Exception as ex:
            if raise_on_fail:
                raise ValueError(INVALID_CTX % src_context) from ex

            context = default

    elif src_context is not None and raise_on_fail:
        raise TypeError(INVALID_CTX % src_context)

    if context is not None and not isinstance(context, dict):
        if raise_on_fail:
            raise TypeError(INVALID_CTX % src_context)

        context = default

    return context


def _prepare_relational_count(
    parent_set,
    field_name,
    expected_type,
    domain=None,
):
    """Prepare common data required to count relational field records.

    The relational field is validated and its domain and context are resolved.
    The field domain is combined with an optional additional domain supplied
    by the caller, and the comodel is configured with the field context.

    Args:
        parent_set (odoo.models.Model): Recordset containing the parent
            records whose related records must be counted.
        field_name (str): Name of the relational field defined on the parent
            model.
        expected_type (str): Expected Odoo relational field type. Typically
            ``"one2many"`` or ``"many2many"``.
        domain (list | tuple | str | callable | None, optional): Additional
            domain to apply to the related records. Defaults to None.

    Returns:
        tuple: A four-item tuple containing the relational field definition,
        the comodel recordset with the field context applied, the combined
        related-record domain and a dictionary initialized to zero for every
        parent record ID.

    Raises:
        TypeError: If ``field_name`` does not identify a field of
            ``expected_type``, or if the field domain, additional domain or
            field context has an unsupported type.
        ValueError: If a domain or context expression cannot be evaluated.
    """
    field = parent_set._fields.get(field_name)

    if not field or field.type != expected_type:
        raise TypeError(
            f"Field {field_name!r} is not a {expected_type} "
            f"on model {parent_set._name}"
        )

    field_domain = evaluate_domain(
        parent_set,
        field.domain,
        default=[],
    )

    extra_domain = evaluate_domain(
        parent_set,
        domain,
        default=[],
    )

    field_context = evaluate_context(
        parent_set,
        field.context,
        default={},
    )

    comodel = parent_set.env[field.comodel_name].with_context(
        **(field_context or {})
    )

    related_domain = AND(
        [
            field_domain or [],
            extra_domain or [],
        ]
    )

    counts = dict.fromkeys(parent_set.ids, 0)

    return field, comodel, related_domain, counts


def one2many_count(parent_set, o2m_field_name, domain=None):
    """Count matching One2many records for each parent record.

    Related records are counted with a single public ORM ``read_group`` call,
    grouped by the inverse Many2one field. Aggregation is therefore performed
    directly by PostgreSQL.

    The domain and context declared on the One2many field are respected,
    together with any additional domain supplied by the caller. Odoo access
    rights, record rules and ``active_test`` behavior are applied by the ORM.

    Args:
        parent_set (odoo.models.Model): Recordset containing the parent
            records whose related records must be counted.
        o2m_field_name (str): Name of the One2many field defined on the parent
            model.
        domain (list | tuple | str | callable | None, optional): Additional
            domain to apply to the related records. Defaults to None.

    Returns:
        dict[int, int]: Mapping from every parent record ID to the number of
        matching related records. Parents without matching records have a
        count of zero.

    Raises:
        TypeError: If ``o2m_field_name`` is not a One2many field, or if a
            domain or context has an unsupported type.
        ValueError: If a domain or context expression cannot be evaluated.
        odoo.exceptions.AccessError: If the current user cannot read the
            related model or the fields involved in the operation.
    """
    field, comodel, related_domain, counts = _prepare_relational_count(
        parent_set,
        o2m_field_name,
        "one2many",
        domain,
    )

    if not parent_set:
        return counts

    related_domain = AND(
        [
            [(field.inverse_name, "in", parent_set.ids)],
            related_domain,
        ]
    )

    grouped_data = comodel.read_group(
        domain=related_domain,
        fields=[field.inverse_name],
        groupby=[field.inverse_name],
        lazy=False,
    )

    for row in grouped_data:
        parent = row.get(field.inverse_name)

        if parent:
            counts[parent[0]] = row["__count"]

    return counts


def many2many_count(parent_set, m2m_field_name, domain=None):
    """Count matching Many2many records for each parent record.

    The comodel domain is converted into an Odoo query so access rights,
    record rules and context-dependent filtering are preserved. The final
    count is performed directly against the Many2many relation table using
    ``odoo.tools.SQL``.

    PostgreSQL performs the aggregation and returns only one row per parent,
    avoiding materialization of every parent-child relation in Python.

    Args:
        parent_set (odoo.models.Model): Recordset containing the parent
            records whose related records must be counted.
        m2m_field_name (str): Name of the Many2many field defined on the
            parent model.
        domain (list | tuple | str | callable | None, optional): Additional
            domain to apply to the related records. Defaults to None.

    Returns:
        dict[int, int]: Mapping from every parent record ID to the number of
        matching related records. Parents without matching records have a
        count of zero.

    Raises:
        TypeError: If ``m2m_field_name`` is not a Many2many field, or if a
            domain or context has an unsupported type.
        ValueError: If a domain or context expression cannot be evaluated.
        odoo.exceptions.AccessError: If the current user cannot read the
            related model or the fields involved in the operation.
    """
    field, comodel, related_domain, counts = _prepare_relational_count(
        parent_set,
        m2m_field_name,
        "many2many",
        domain,
    )

    if not parent_set:
        return counts

    child_query = comodel._search(related_domain)

    relation_table = SQL.identifier(field.relation)
    parent_column = SQL.identifier(field.column1)
    child_column = SQL.identifier(field.column2)

    sql = SQL(
        """
        SELECT %(parent_column)s, COUNT(*)
          FROM %(relation_table)s
         WHERE %(parent_column)s = ANY(%(parent_ids)s)
           AND %(child_column)s IN %(child_query)s
         GROUP BY %(parent_column)s
        """,
        parent_column=parent_column,
        relation_table=relation_table,
        parent_ids=parent_set.ids,
        child_column=child_column,
        child_query=child_query.subselect(),
    )

    for parent_id, count in parent_set.env.execute_query(sql):
        counts[parent_id] = count

    return counts


def one2many_count_search_domain(
    parent_set,
    o2m_field_name,
    operator,
    value,
    domain=None,
):
    """Build a parent domain by comparing One2many record counts.

    Matching related records are grouped by the inverse Many2one field using
    a single public ORM ``read_group`` call. Parents absent from the grouped
    result are treated as having a count of zero.

    The domain and context declared on the One2many field are respected,
    together with any additional domain supplied by the caller. Odoo access
    rights, record rules and ``active_test`` behavior are applied by the ORM.

    Args:
        parent_set (odoo.models.Model): Recordset of the parent model.
        o2m_field_name (str): Name of the One2many field defined on the
            parent model.
        operator (str): Comparison operator to apply to the related-record
            count.
        value (int | bool): Value to compare against the related-record count.
        domain (list | tuple | str | callable | None, optional): Additional
            domain to apply to the related records. Defaults to None.

    Returns:
        list: ORM domain to apply to the parent model.

    Raises:
        TypeError: If ``o2m_field_name`` is not a One2many field, or if a
            domain or context has an unsupported type.
        ValueError: If a domain or context expression cannot be evaluated.
        odoo.exceptions.AccessError: If the current user cannot read the
            related model or the fields involved in the operation.
    """
    if value is True:
        return TRUE_DOMAIN if operator == "=" else FALSE_DOMAIN

    if value is False:
        return TRUE_DOMAIN if operator != "=" else FALSE_DOMAIN

    compare = OPERATOR_MAP.get(operator)
    if not compare:
        return FALSE_DOMAIN

    field, comodel, related_domain, _counts = _prepare_relational_count(
        parent_set,
        o2m_field_name,
        "one2many",
        domain,
    )

    grouped_data = comodel.read_group(
        domain=related_domain,
        fields=[field.inverse_name],
        groupby=[field.inverse_name],
        lazy=False,
    )

    counts = {}

    for row in grouped_data:
        parent = row.get(field.inverse_name)

        if parent:
            counts[parent[0]] = row["__count"]

    if compare(0, value):
        excluded_ids = [
            parent_id
            for parent_id, count in counts.items()
            if not compare(count, value)
        ]

        if not excluded_ids:
            return TRUE_DOMAIN

        return [("id", "not in", excluded_ids)]

    matched_ids = [
        parent_id
        for parent_id, count in counts.items()
        if compare(count, value)
    ]

    if not matched_ids:
        return FALSE_DOMAIN

    return [("id", "in", matched_ids)]


def get_available_copy_value(
    record,
    field_name,
    value,
    domain=None,
    max_length=None,
):
    """Return the first available numbered value when copying a record.

    Any trailing numeric suffix is removed from the original value before
    candidates are generated. Candidates are built by appending consecutive
    integers starting at 1 until an unused value is found.

    Args:
        record (odoo.models.Model): Record being copied.
        field_name (str): Field whose value must be available.
        value (str): Original field value.
        domain (list | tuple | None, optional): Additional domain restricting
            the records checked for existing values. Defaults to None.
        max_length (int | None, optional): Maximum length allowed for the
            generated value. Defaults to None.

    Returns:
        str: First available value.

    Raises:
        ValueError: If ``max_length`` is not a positive integer or becomes too
            small to contain the numeric suffix.
    """
    record.ensure_one()

    if max_length is not None and max_length <= 0:
        raise ValueError("Maximum length must be greater than zero")

    domain = list(domain or [])

    base_value = sub(r"[0-9]+$", "", value or "")
    model = record.env[record._name]

    index = 1

    while True:
        suffix = str(index)

        if max_length is not None:
            available_length = max_length - len(suffix)

            if available_length < 0:
                raise ValueError(
                    "Maximum length is too small for the generated suffix"
                )

            candidate = f"{base_value[:available_length]}{suffix}"
        else:
            candidate = f"{base_value}{suffix}"

        candidate_domain = domain + [
            (field_name, "=", candidate),
        ]

        if not model.search_count(candidate_domain, limit=1):
            return candidate

        index += 1


def check_unique_value(
    record,
    field_name,
    value=None,
    domain=None,
    operator="=",
    message=None,
):
    """Ensure a field value is unique within an optional record scope.

    The helper searches for another record of the same model whose
    ``field_name`` matches ``value`` according to the supplied Odoo domain
    ``operator``. The current record is always excluded from the search.

    An additional ``domain`` can be supplied to restrict the scope in which
    uniqueness must be enforced. The domain is evaluated through
    ``evaluate_domain()`` using ``record`` as its evaluation recordset.
    Consequently, it may be provided as a list, tuple, string expression or
    callable, following the same rules supported by that helper.

    A callable domain is particularly useful when the uniqueness scope depends
    on values of the record being checked. For example, to require a facility
    name to be unique only within its complex:

        domain=lambda record: [
            ("complex_id", "=", record.complex_id.id),
        ]

    If ``value`` is not explicitly provided, the current value of
    ``field_name`` is obtained from ``record``.

    The comparison operator defaults to ``"="``. Callers can use another
    valid Odoo domain operator when different comparison semantics are
    required. For example, ``"=ilike"`` can be used to enforce
    case-insensitive uniqueness for textual values.

    The search is performed using the environment and context of ``record``.
    The helper therefore preserves access rights, record rules and
    context-dependent ORM behavior. It does not implicitly apply ``sudo()``
    or modify ``active_test``. Callers requiring those semantics must prepare
    the record beforehand, for example:

        check_unique_value(
            record.sudo().with_context(active_test=False),
            field_name="name",
        )

    This also allows the helper to work with translated fields. If ``record``
    contains a specific ``lang`` in its context, both the value lookup and the
    duplicate search use Odoo's normal translated-field semantics, including
    translation fallback.

    Args:
        record (odoo.models.Model): Single record whose field value must be
            checked. Its environment and context are preserved for the
            duplicate search.
        field_name (str): Name of the field whose value must be unique.
        value (Any | None, optional): Value to compare against existing
            records. If None, the current value of ``field_name`` is read from
            ``record``. Defaults to None.
        domain (list | tuple | str | callable | None, optional): Additional
            domain restricting the records among which uniqueness is checked.
            Callable domains receive ``record`` as their argument. Defaults
            to None.
        operator (str, optional): Odoo domain operator used to compare
            ``field_name`` with ``value``. Defaults to ``"="``.
        message (str | None, optional): Error message used when a duplicate is
            found. If omitted, a generic duplicate-record message is used.

    Returns:
        None: The function returns normally when no duplicate record exists.

    Raises:
        ValueError: If ``field_name`` does not exist on the record model, or
            if the additional domain cannot be evaluated.
        TypeError: If ``domain`` has an unsupported type or does not evaluate
            to a valid domain structure.
        ValidationError: If another record matching the uniqueness criteria
            exists.

    Notes:
        This helper provides ORM-level uniqueness validation. It does not
        provide the concurrency guarantees of a PostgreSQL ``UNIQUE``
        constraint. Two concurrent transactions could theoretically pass the
        validation before either transaction is committed.
    """
    record.ensure_one()

    if field_name not in record._fields:
        pattern = _lt("Field {} does not exist on model {}")
        raise ValueError(pattern.format(field_name, record._name))

    if value is None:
        value = getattr(record, field_name)

    message = message or _lt("Duplicate record found")

    domain = evaluate_domain(record, domain, default=[])

    domain = list(domain or [])
    domain.extend([("id", "!=", record.id), (field_name, operator, value)])

    if record.search_count(domain, limit=1):
        error_message = f"{message}. ({field_name} = {value})"
        raise ValidationError(error_message)


def check_unique_translation(
    recordset,
    field_name,
    domain=None,
    operator="=ilike",
    message=None,
):
    """Ensure a translated field is unique in every installed language.

    The uniqueness check is performed using the effective value returned by
    Odoo for each installed language, not only the translation explicitly
    stored for that language.

    For every record and every installed language, the record is evaluated
    with that language set in the context. The helper then delegates the
    duplicate lookup to ``check_unique_value()``, passing the language-specific
    record, the effective translated value, the optional uniqueness domain and
    the requested comparison operator.

    An additional ``domain`` can be supplied to restrict the scope in which
    translated values must be unique. The domain is passed unchanged to
    ``check_unique_value()``, which evaluates it for each individual record
    through ``evaluate_domain()``.

    This allows dynamic scopes based on the record being checked. For example,
    to require a facility name to be unique only within its complex:

        domain=lambda record: [
            ("complex_id", "=", record.complex_id.id),
        ]

    By default, ``operator="=ilike"`` is used. This makes uniqueness
    case-insensitive, so values such as ``"Monday"``, ``"MONDAY"`` and
    ``"monday"`` are considered duplicates within the same effective language
    and uniqueness scope.

    Callers can provide another valid Odoo domain operator when different
    comparison semantics are required.

    Odoo translated ``Char`` fields use ``en_US`` as fallback when no explicit
    value is stored for the requested language. Consequently, fallback values
    also participate in the uniqueness check.

    For example, given:

        Record A:
            en_US = "Monday"
            es_ES = False

        Record B:
            en_US = "Other"
            es_ES = "Monday"

    both records have the effective value ``"Monday"`` when evaluated with
    ``lang="es_ES"``. The helper therefore considers them duplicates in
    Spanish, even though Record A has no explicit Spanish translation stored.

    Uniqueness is enforced independently for each installed language context.
    Values are not compared across different languages. Therefore, the same
    textual value may exist in different languages as long as it is unique
    within each language's effective values and within the supplied domain.

    Archived records are included in the duplicate search because each
    language-specific record is evaluated with ``active_test=False``. This
    prevents archived records from releasing translated values that are
    expected to remain unique.

    The helper does not apply ``sudo()``. Access rights and record rules are
    inherited from ``recordset``. If duplicate detection must ignore record
    rules, callers should pass a sudoed recordset, for example:

        check_unique_translation(
            recordset.sudo(),
            field_name="name",
        )

    Args:
        recordset (odoo.models.Model): Recordset whose translated field values
            must be checked. Its environment and access mode are preserved.
        field_name (str): Name of the translated field to validate.
        domain (list | tuple | str | callable | None, optional): Additional
            domain restricting the records among which each translated value
            must be unique. Callable domains are evaluated for each individual
            record. Defaults to None.
        operator (str, optional): Odoo domain operator used to determine
            whether two effective translated values are duplicates. Defaults
            to ``"=ilike"`` for case-insensitive comparison.
        message (str | None, optional): Error message used when a duplicate is
            found. If omitted, ``check_unique_value()`` uses its default
            duplicate-record message.

    Returns:
        None: The function returns normally when no duplicate translated value
        exists in any installed language.

    Raises:
        ValueError: If ``field_name`` does not exist on the model, if the
            referenced field is not translatable, or if the supplied domain
            cannot be evaluated.
        TypeError: If ``domain`` has an unsupported type or does not evaluate
            to a valid domain structure.
        ValidationError: If another record has the same effective translated
            value in any installed language according to ``operator`` and the
            supplied uniqueness domain.

    Notes:
        This helper provides ORM-level uniqueness validation. It does not
        provide the concurrency guarantees of a PostgreSQL ``UNIQUE``
        constraint. Two concurrent transactions could theoretically pass the
        validation before either transaction is committed.
    """
    field = recordset._fields.get(field_name)

    if not field:
        pattern = _lt("Field {} does not exist on model {}")
        raise ValueError(pattern.format(field_name, recordset._name))

    if not field.translate:
        pattern = _lt("Field {} on model {} is not translatable")
        raise ValueError(pattern.format(field_name, recordset._name))

    language_list = recordset.env["res.lang"].get_installed()

    for record in recordset:
        for code, _name in language_list:
            record_ctx = record.with_context(lang=code, active_test=False)

            value = getattr(record_ctx, field_name)
            if not value:
                continue

            check_unique_value(
                record_ctx,
                field_name=field_name,
                value=value,
                domain=domain,
                operator=operator,
                message=message,
            )
