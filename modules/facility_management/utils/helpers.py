# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################


try:
    # Odoo 14+ (incl. 18): class name is `Expression`
    from odoo.osv.expression import AND, Expression
except ImportError:  # older Odoo (e.g. 13)
    from odoo.osv.expression import AND, expression as Expression

from odoo.tools.translate import _
from odoo.tools.safe_eval import safe_eval
from operator import eq, ne, lt, le, gt, ge


INVALID_DOMAIN = _('Given domain expression %r is not a valid ORM domain')
INVALID_CTX = _('Given context expression %r is not a valid context mapping')

OPERATOR_MAP = {
    '=': eq,
    '!=': ne,
    '<': lt,
    '<=': le,
    '>': gt,
    '>=': ge,
}

def evaluate_domain(recordset, src_domain, default=None, raise_on_fail=True):
    """
    Evaluate a field domain definition into a valid ORM domain.

    The source domain (`src_domain`) can be defined in multiple forms:
      * list/tuple: already a valid domain, returned as-is.
      * str: evaluated with ``safe_eval`` in a context containing only
        ``context = recordset.env.context``.
      * callable: invoked with the given recordset to obtain the domain.

    Args:
        recordset (odoo.models.Model):
            Recordset used to provide ``env`` and passed to callables.
        src_domain (list | tuple | str | callable):
            The source domain definition to evaluate.
        default (list | tuple | None, optional):
            Fallback value returned if the domain cannot be evaluated and
            ``raise_on_fail`` is False. Defaults to None.
        raise_on_fail (bool, optional):
            If True, raise a ValueError/TypeError when the domain cannot be
            evaluated or is not a list/tuple. If False, return ``default``.

    Returns:
        list | tuple | None:
            A valid domain (list/tuple). If evaluation fails and
            ``raise_on_fail`` is False, returns ``default`` (commonly None).

    Raises:
        ValueError: If evaluation of string/callable fails and
            ``raise_on_fail`` is True.
        TypeError: If the result is not a list/tuple and
            ``raise_on_fail`` is True.
    """

    domain = default

    if isinstance(src_domain, (list, tuple)):
        domain = list(src_domain)

    elif isinstance(src_domain, str):
        try:
            # Evaluate with a minimal context; client-style domains often
            # reference `context`.
            minimal_ctx = {'context': recordset.env.context}
            domain = safe_eval(src_domain, minimal_ctx)
        except Exception as ex:
            if raise_on_fail:
                raise ValueError(INVALID_DOMAIN % src_domain) from ex
            domain = default

    elif callable(src_domain):
        try:
            # Field callable is invoked with a recordset
            domain = src_domain(recordset)
        except Exception as ex:
            if raise_on_fail:
                raise ValueError(INVALID_DOMAIN % src_domain) from ex
            domain = default

    if domain is not None and not isinstance(domain, (list, tuple)):
        # Ensure a proper domain structure
        if raise_on_fail:
            raise TypeError(INVALID_DOMAIN % src_domain)
        domain = default

    return domain


def evaluate_context(recordset, src_context, default=None, raise_on_fail=True):
    context = default

    if isinstance(src_context, dict):
        context = src_context
    
    elif isinstance(src_context, str):
        # Evaluate with minimal context
        try:
            minimal_ctx = {'context': recordset.env.context}
            context = safe_eval(src_context, minimal_ctx)
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

    if context is not None and not isinstance(context, dict):
        # Ensure a proper context structure
        if raise_on_fail:
            raise TypeError(INVALID_CTX % src_context)
        context = default

    return context


def one2many_count(parent_set, o2m_field_name, domain=None):
    """
    Count related records for a One2many field.

    This function uses `read_group` to efficiently count child records grouped
    by the inverse Many2one field.

    Args:
        parent_set (recordset):
            Recordset of the parent model (e.g. facility.complex).
        o2m_field_name (str):
            Name of the One2many field on the parent model. The comodel and
            its inverse Many2one are introspected from this field.
        domain (list, optional):
            Additional domain to restrict child records. Defaults to None.

    Returns:
        dict:
            A dictionary mapping parent record IDs to the number of active
            related records. If the comodel does not have an `active` field,
            counts will include inactive records.
    """

    # Validate One2many field first (even if parent_set is empty)
    field = parent_set._fields.get(o2m_field_name)
    if not field or field.type != 'one2many':
        raise TypeError(
            "Field %r is not a one2many on model %s"
            % (o2m_field_name, parent_set._name)
        )

    inverse_name = field.inverse_name
    domain_attribute = field.domain
    
    # Initialize result with zeros for all parent IDs
    counts = {cid: 0 for cid in parent_set.ids}
    if not parent_set:
        return counts

    # Prepare comodel environment and base domain (children pointing to parents)
    comodel_obj = parent_set.env[field.comodel_name]
    comodel_domain = [(inverse_name, 'in', parent_set.ids)]

    domain_list = [comodel_domain]

    # Append one2many field domain
    if domain_attribute:
        field_domain = evaluate_domain(parent_set, field.domain, default=None)
        if field_domain:
            domain_list.append(field_domain)

    # Resolve active_test from context and append domain to the domain list
    context_attribute = getattr(field, 'context', None)
    field_context = evaluate_context(
        parent_set, context_attribute, default=None, raise_on_fail=False
    )
    if isinstance(field_context, dict) and 'active_test' in field_context:
        active_test = bool(field_context['active_test'])
    else:
        active_test = bool(parent_set.env.context.get('active_test', True))

    if active_test and 'active' in comodel_obj.fields_get(['active']):
        domain_list.append([('active', '=', True)])

    # Append additional domain if provided
    if domain:
        domain_list.append(domain)

    # Perform grouped read to aggregate counts
    data = comodel_obj.read_group(
        domain=AND(domain_list),
        fields=[inverse_name],
        groupby=[inverse_name],
        lazy=False,
    )

    # Populate results: skip rows with null inverse_name
    for row in data:
        key = row.get(inverse_name)
        if not key:
            # Skip children without a parent (NULL inverse)
            continue

        cid = key[0]
        counts[cid] = row['__count']

    return counts


def many2many_count(parent_set, m2m_field_name, domain=None):
    """
    Count related records for a Many2many field using a single SQL query.

    The function inspects the M2M field on the parent model to get the relation
    table and join columns, converts the child domain to SQL via Odoo's query
    builder, and applies it with an EXISTS subquery. This avoids fetching child
    IDs in Python and eliminates the need for chunking.

    Args:
        parent_set (recordset):
            Recordset of the parent model holding the M2M field.
        m2m_field_name (str):
            Name of the M2M field defined on the parent model.
        domain (list | tuple | None, optional):
            Additional domain applied on the child comodel. Defaults to None.

    Returns:
        dict:
            Mapping {parent_id: count_of_children}. Parents not present in the
            relation get 0.
    """
    # Initialize result for provided parents (empty set is valid)
    counts = {pid: 0 for pid in parent_set.ids}
    if not parent_set:
        return counts

    # Validate and introspect the M2M field from the parent model
    field = parent_set._fields.get(m2m_field_name)
    if not field or field.type != 'many2many':
        raise TypeError(
            "Field %r is not a many2many on model %s"
            % (m2m_field_name, parent_set._name)
        )

    rel_table = field.relation
    col_parent = field.column1      # FK to parent table
    col_child = field.column2       # FK to child (comodel) table
    child_model = parent_set.env[field.comodel_name]
    child_table = child_model._table
    
    # Build child domain parts: field.domain (if any), user domain, active_test
    domain_list = []

    # Resolve field domain attribute and append it to the domain list
    domain_attribute = getattr(field, 'domain', None)
    if domain_attribute:
        field_domain = evaluate_domain(
            parent_set, domain_attribute, default=None, raise_on_fail=False
        )
        if field_domain:
            domain_list.append(field_domain)
  
    # Resolve active_test from context and append domain to the domain list
    context_attribute = getattr(field, 'context', None)
    field_context = evaluate_context(
        parent_set, context_attribute, default=None, raise_on_fail=False
    )
    if isinstance(field_context, dict) and 'active_test' in field_context:
        active_test = bool(field_context['active_test'])
    else:
        active_test = bool(parent_set.env.context.get('active_test', True))

    if active_test and 'active' in child_model.fields_get(['active']):
        domain_list.append([('active', '=', True)])

    # Append given domain if was set
    if domain:
        domain_list.append(domain)

    # Join all resolved domains
    child_domain = AND(domain_list) if domain_list else []

    # Convert domain to SQL using `expression` + apply record rules
    expr = Expression(child_domain, child_model, alias=child_table)
    query = expr.query
    child_model._apply_ir_rules(query, 'read')
    from_clause = query.from_clause.code
    where_clause = query.where_clause.code
    params = query.where_clause.params

    # Compose SQL with EXISTS to avoid row multiplication on complex joins
    cr = parent_set.env.cr
    parent_ids = tuple(parent_set.ids)

    sql = f"""
        SELECT 
            mid_rel.{col_parent} AS parent_id,
            COUNT(mid_rel.{col_child}) AS cnt
        FROM {rel_table} AS mid_rel
        WHERE mid_rel.{col_parent} IN %s
          AND EXISTS (
                SELECT 1
                FROM {from_clause}
                WHERE "id" = mid_rel.{col_child}
                  AND ({where_clause or 'TRUE'})
          )
        GROUP BY mid_rel.{col_parent}
    """

    # First param: parent_ids array for ANY(%s); then child-domain params
    cr.execute(sql, [parent_ids, *params])
    for parent_id, cnt in cr.fetchall():
        counts[parent_id] = cnt

    return counts
