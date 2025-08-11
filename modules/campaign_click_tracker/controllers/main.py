# -*- coding: utf-8 -*-
###############################################################################
#    License, author and contributors information in:                         #
#    __openerp__.py file at the root folder of this module.                   #
###############################################################################

from odoo.http import Controller, request, route
from odoo.tools.translate import _
from logging import getLogger
from odoo.tools import format_datetime
from werkzeug.exceptions import Forbidden, Conflict, InternalServerError
from werkzeug.wrappers import Response as WerkzeugResponse

_logger = getLogger(__name__)

ANSWER_URL = '/campaign_click_tracker/answer/<string:input_token>/<string:answer_token>'
SHOW_URL = '/campaign_click_tracker/show/<string:input_token>'


class PublishTimesheets(Controller):
    """
    """

    @route(ANSWER_URL, type='http', auth='public', website=True, csrf=False)
    def campaign_click_tracker(self, input_token, answer_token, **kw):
        user_input = self._search_for_user_input(input_token)
        if not user_input:
            return self._notify_error(
                title=_("Access Denied"),
                message=_("No answer is expected from this user."),
                status=403,
                log_message="click_tracker: invalid input token '%s'" % input_token
            )


        campaign = user_input.campaign_id
        if not self._is_valid_answer_token(campaign, answer_token):
            return self._notify_error(
                title=_("Invalid Response"),
                message=_("This answer does not belong to the user's campaign."),
                status=409,
                log_message="click_tracker: invalid answer token '%s'" % answer_token
            )

        answer = self._search_for_available_answer(answer_token)
        if not answer:
            return self._notify_error(
                title=_("Unexpected Error"),
                message=_("The requested answer could not be retrieved."),
                status=500,
                log_message="click_tracker: answer with token '%s' could not be retrieved" % answer_token
            )

        if not self._update_answer(user_input, answer):
            return self._notify_error(
                title=_("Unexpected Error"),
                message=_("Unexpected error while recording response."),
                status=500,
                log_message="click_tracker: failed to assign answer ID %s to user_input ID %s" % (
                    answer.id, user_input.id
                )
            )

        return self._render_response(user_input, allow_comments=True)

    def _search_for_user_input(self, input_token):
        model = 'campaign.click.tracker.user.input'
        user_input = request.env[model].sudo()

        domain = [
            ('token', '=', input_token),
            ('active', '=', True),
        ]
        user_input = user_input.search(domain, limit=1)

        return user_input

    def _is_valid_answer_token(self, campaign, answer_token):
        valid_tokens = campaign.mapped('available_answer_ids.token')
        return answer_token in valid_tokens

    def _search_for_available_answer(self, answer_token):
        model = 'campaign.click.tracker.answer'
        answer = request.env[model].sudo()

        domain = [
            ('token', '=', answer_token),
            ('active', '=', True),
        ]
        answer = answer.search(domain, limit=1)

        return answer

    def _update_answer(self, user_input, answer):
        try:
            return user_input.write({'answer_id': answer.id})
        except Exception as e:
            pattern = "Failed to update answer for user_input %s: %s"
            _logger.exception(pattern, user_input.id, str(e))
            return False

    def _render_response(self, user_input, allow_comments=False):
        formatted_date = format_datetime(
            request.env, user_input.write_date, tz=request.context.get('tz')
        )
        template = 'campaign_click_tracker.response_recorded_template'
        show_url = SHOW_URL.replace('<string:input_token>', user_input.token)
        page_title = user_input.campaign_id.name or _('Click tracker')
        page_title += f' ‒ {user_input.extra}' if user_input.extra else ''

        return request.render(template, {
            'user_input': user_input,
            'recorded_at': formatted_date,
            'allow_comments': allow_comments,
            'show_url': show_url,
            'page_title': page_title
        })

    @route(SHOW_URL, type='http', auth='public', website=True, csrf=False, methods=['POST', 'GET'])
    def submit_comment(self, input_token, **post):
        if request.httprequest.method != 'POST':  # Prevent 405 (Method Not Allowed)
            return self._notify_error(
                title=_("Link Expired"),
                message=_("This page is no longer available. The link has expired ¯\\_(ツ)_/¯."),
                status=410,
                log_message="click_tracker: expired link access for token '%s'" % input_token
            )

        comment = post.get('comment', '').strip()

        user_input = self._search_for_user_input(input_token)
        if not user_input:
            return self._notify_error(
                title=_("Access Denied"),
                message=_("No comment is expected from this user."),
                status=403,
                log_message="click_tracker: invalid input token '%s'" % input_token
            )

        if comment:
            user_input.comment = comment
            _logger.info("Comment saved for user_input %s", user_input.id)

        return self._render_response(user_input, allow_comments=False)

    def _notify_error(self, title, message, status=403, log_message=None):
        log_message = log_message or message
        _logger.error(log_message) 

        view_obj = request.env['ir.ui.view']
        template_xid = 'campaign_click_tracker.error_template'

        data = {'title': title, 'message': message}
        html = view_obj.render_template(template_xid, data)
        
        return WerkzeugResponse(
            html, status=403, content_type='text/html; charset=utf-8'
        )
