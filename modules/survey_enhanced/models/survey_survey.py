# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from odoo import models, fields, api
from odoo.tools.translate import _
from odoo.tools import safe_eval

from urllib.parse import urlparse, urlunparse
from logging import getLogger


_logger = getLogger(__name__)


class SurveySurvey(models.Model):
    """
    """

    _name = 'survey.survey'
    _inherit = 'survey.survey'

    website_id = fields.Many2one(
        string='Website',
        required=False,
        readonly=False,
        index=True,
        default=None,
        help=False,
        comodel_name='website',
        domain=[],
        context={},
        ondelete='cascade',
        auto_join=False
    )

    custom_css = fields.Text(
        string='Custom css',
        required=False,
        readonly=False,
        index=False,
        default=None,
        help='Custom CSS to be used in frontend',
        translate=False
    )

    question_and_page_count = fields.Integer(
        string='No. sections/questions',
        required=True,
        readonly=True,
        index=False,
        default=0,
        help='Total number of questions including section pages',
        compute='_compute_question_and_page_count'
    )

    @api.depends('question_and_page_ids')
    def _compute_question_and_page_count(self):
        for record in self:
            value = len(record.question_and_page_ids)
            record.question_and_page_count = value

    def view_question_and_page(self):
        self.ensure_one()

        action_xid = 'survey.action_survey_question_form'
        act_wnd = self.env.ref(action_xid)

        name = _('Sections and questions')

        context = self.env.context.copy()
        context.update(safe_eval(act_wnd.context))
        context.update({'default_related_field': self.id})

        domain = [('survey_id', '=', self.id)]

        serialized = {
            'type': 'ir.actions.act_window',
            'res_model': act_wnd.res_model,
            'target': 'current',
            'name': name,
            'view_mode': act_wnd.view_mode,
            'domain': domain,
            'context': context,
            'search_view_id': act_wnd.search_view_id.id,
            'help': act_wnd.help
        }

        return serialized

    def _compute_survey_url(self):
        config = self.env['ir.config_parameter'].sudo()
        base_url = config.get_param('web.base.url')

        for survey in self:
            if survey.website_id and survey.website_id.domain:
                survey_url = survey.website_id.domain
            else:
                survey_url = base_url

            relative_url = "survey/start/%s" % (survey.access_token)
            survey.public_url = self.complete_url(survey_url, relative_url)

    @staticmethod
    def complete_url(domain, path):
        parsed = urlparse(domain)
        if not parsed.scheme:
            parsed = parsed._replace(scheme='https')
        return urlunparse(parsed._replace(path=f"/{path}"))
