# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.exceptions import ValidationError

from datetime import timedelta
from logging import getLogger


_logger = getLogger(__name__)


class FacilityReportingWizard(models.TransientModel):
    _name = "facility.reporting.wizard"
    _description = "Facility reporting wizard"

    _rec_name = "id"
    _order = "id DESC"

    date_start = fields.Datetime(
        string="Beginning",
        required=True,
        readonly=False,
        index=True,
        default=lambda self: self.week_start(),
        help="Date/time of session start",
    )

    @api.onchange("date_start")
    def _onchange_date_start(self):
        for record in self:
            if record.date_stop <= record.date_start:
                record.date_stop = record.date_start

    date_stop = fields.Datetime(
        string="Ending",
        required=True,
        readonly=False,
        index=True,
        default=lambda self: self.week_start() + timedelta(days=6),
        help="Date/time of session end",
    )

    full_weeks = fields.Boolean(
        string="Full weeks",
        required=False,
        readonly=False,
        index=False,
        default=True,
        help="Always show full weeks",
    )

    facility_ids = fields.Many2many(
        string="Facilities",
        required=False,
        readonly=False,
        index=False,
        default=lambda self: self._default_facility_ids(),
        help="Target facilities",
        comodel_name="facility.facility",
        relation="facility_reporting_wizard_rel",
        column1="wizard_id",
        column2="facility_id",
        domain=[],
        context={},
    )

    def _default_facility_ids(self):
        recordset = self.env["facility.facility"]
        active_model, active_ids = self._get_from_context()

        if active_model and active_ids:
            domain = [("id", "in", active_ids)]
            recordset = self.env[active_model].search(domain)
            if active_model == "facility.complex":
                recordset = recordset.mapped("facility_ids")

        return recordset

    report_type = fields.Selection(
        string="Report presentation",
        required=True,
        readonly=False,
        index=False,
        default="qweb-pdf",
        help=(
            "Choose how the report will be presented: as a printable PDF "
            "document or as a web page in the browser."
        ),
        selection=[
            ("qweb-pdf", "Printable PDF document"),
            ("qweb-html", "Web page (in browser)"),
        ],
    )

    @api.onchange("report_type")
    def _onchange_report_type(self):
        for record in self:
            if record.report_type == "qweb-html":
                record.close_on_report_download = True

    close_on_report_download = fields.Boolean(
        string="Close wizard",
        required=False,
        readonly=False,
        index=False,
        default=True,
        help="Check it to close wizard on report download",
    )

    @staticmethod
    def week_start():
        present = fields.Datetime.now()
        today = present.replace(hour=0, minute=0, second=0, microsecond=0)

        return today - timedelta(today.weekday())

    @api.model
    def _get_from_context(self):
        active_model = self.env.context.get("active_model", None)
        if not self._is_valid_model(active_model):
            active_model = None

        active_ids = self.env.context.get("active_ids", [])
        if not active_ids:
            active_id = self.env.context.get("active_id", False)
            if active_id:
                active_ids = [active_id]

        return active_model, active_ids

    @staticmethod
    def _is_valid_model(model):
        valid = ["facility.facility", "facility.complex"]
        return model in valid

    def _with_referrer(self):
        """Update context to communicate that the referrer will be this wizard

        Returns:
            Model: ``self`` with the updated context
        """
        ctx = self.env.context.copy()

        ctx.update(
            {
                "active_model": self._name,
                "active_id": self.id,
                "active_ids": [],
            }
        )

        return self.with_context(ctx)

    def _validate(self):
        self.ensure_one()

        if self.date_stop < self.date_start:
            msg = _("The interval cannot end without having started")
            raise ValidationError(msg)

        if not self.facility_ids:
            msg = _("You have not selected any facility")
            raise ValidationError(msg)

    def reporting(self):
        self.ensure_one()

        self._validate()

        action_xid = "{module}.{name}".format(
            module="facility_management",
            name="action_report_facility_reservations",
        )
        self_ctx = self._with_referrer()
        act_report = self_ctx.env.ref(action_xid)

        datas = dict(
            date_start=self.date_start,
            date_stop=self.date_stop,
            full_weeks=self.full_weeks,
            docids=self.facility_ids.ids,
        )

        action = act_report.report_action(self.facility_ids, data=datas)

        action["close_on_report_download"] = (
            self.report_type == "qweb-html" or self.close_on_report_download
        )
        action["report_type"] = self.report_type

        return action
