# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.tools import drop_view_if_exists

from datetime import datetime
from logging import getLogger


_logger = getLogger(__name__)


class MaterializedView(models.AbstractModel):
    """ Abstract model representing a PostgreSQL materialized view in Odoo.
    This model provides a framework for creating Odoo models based on
    materialized views, enabling efficient data retrieval and handling.
    It serves as a base for developing custom models that directly
    interface with underlying materialized views for enhanced performance
    and complex data aggregation capabilities.
    """

    _name = 'materialized.view.abstract'
    _description = ('Abstract model representing a PostgreSQL materialized '
                    'view in Odoo')

    _auto = False
    _view_sql = '''
        SELECT
            ROW_NUMBER() OVER()::INTEGER AS "id",
            1::INTEGER AS create_uid,
            CURRENT_TIMESTAMP(0) AS create_date,
            1::INTEGER AS write_uid,
            CURRENT_TIMESTAMP(0) AS write_date
    '''

    def init(self):
        self._drop_materialized_view_if_exists()
        self._create_materialized_view()

    @api.model
    def _create_materialized_view(self):
        pattern = 'CREATE MATERIALIZED VIEW IF NOT EXISTS {} as ( {} )'
        sentence = pattern.format(self._table, self._view_sql)

        _logger.debug(f'Creating materialized view {self._table}')
        self.env.cr.execute(sentence)

    @api.model
    def _drop_materialized_view_if_exists(self):
        sentence = f'DROP MATERIALIZED VIEW IF EXISTS {self._table} CASCADE;'

        _logger.debug(f'Dropping materialized view {self._table}')
        self.env.cr.execute(sentence)

    @api.model
    def refresh_materialized_view(self, concurrently=True):
        concurrently = 'CONCURRENTLY' if concurrently else ''
        sentence = f'REFRESH MATERIALIZED VIEW {concurrently} {self._table};'

        _logger.debug(f'Refreshing materialized view {self._table}')
        self.env.cr.execute(sentence)

    @api.model
    def _get_last_record_write_date(self):
        model = self.sudo()
        record = model.search([], order='__last_update desc', limit=1)

        return record.write_date if record else None

    @api.model
    def _get_last_cron_execution_time(self):
        cron_task_xid = 'materialized_views.ir_cron_refresh_materialized_views'
        cron_task = self.env.ref(cron_task_xid, False)

        # Si el cron existe, devuelve la última hora de ejecución
        if cron_task:
            return cron_task.lastcall
        else:
            return datetime.min

    @api.model
    def cron_task(self):
        target_type = type(self)

        _logger.info(f'The materialized view update process has started')

        lastcall = self._get_last_cron_execution_time()

        for model_name, model_obj in self.env.items():
            if not isinstance(model_obj, target_type):
                continue

            last_update = model_obj._get_last_record_write_date()
            if last_update and last_update < lastcall:
                model_obj.refresh_materialized_view()

        _logger.info(f'The materialized view update process has finished')
