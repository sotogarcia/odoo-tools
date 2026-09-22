###############################################################################
#    License, author and contributors information in:                         #
#    __manifest__.py file at the root folder of this module.                  #
###############################################################################


from operator import eq, ge, gt, le, lt, ne
from re import sub

from odoo.osv.expression import AND, FALSE_DOMAIN, TRUE_DOMAIN
from odoo.tools import SQL
from odoo.tools.safe_eval import safe_eval
from odoo.tools.translate import _lt

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
