/*odoo.define('academy_timesheets.web_calendar', function (require) {
    "use strict";

    var core = require('web.core');
    var QWeb = core.qweb;
    var session = require('web.session');

    var CalendarController = require("web.CalendarController");

    var CalendarFilterToggleButtonView = {

        renderButtons: function ($node) {
            var result = this._super.apply(this, arguments);

            let button_id = '#8D57C95F9A7E4AE995333FD77E0918E6';
            let button = this.$el.find(button_id)

            button.on('click', this.proxy('calendarFilterToggleItems'));

            return result;
        },

        calendarFilterToggleItems: function(event) {
            let button = jQuery(event.target);
            let calendar_filter = button.parent();
            calendar_filter.find('input').click();
        },

    };

    CalendarController.include(CalendarFilterToggleButtonView);
});*/


odoo.define('academy_timesheets.web_calendar', function(require) {
    "use strict";

    var CalendarRenderer = require('web.CalendarRenderer');

    var includeDict = {
 /*       start: function () {
            var result = this._super.apply(this, arguments);

            console.log('start', this);

            return result;
        },

        _render: function () {
            var result = this._super.apply(this, arguments);

            console.log('_render', this);

            return result;
        },
*/
        _renderFilters: function () {
            var result = this._super.apply(this, arguments);
            var self = this;

            return result.then(function(value) {
                let button_id = '#8D57C95F9A7E4AE995333FD77E0918E6';
                let button = self.$el.find(button_id)

                button.on('click', self.proxy('calendarFilterToggleItems'));
            });
        },

        calendarFilterToggleItems: function(event) {
            let button = jQuery(event.target);
            let calendar_filter = button.parent();
            calendar_filter.find('input').click();
        },

    };

    CalendarRenderer.include(includeDict);
});
