odoo.define('facility_management.header_view_buttons', function (require) {
    "use strict";

    var core = require('web.core');
    var QWeb = core.qweb;
    var session = require('web.session');

    var KanbanController = require("web.KanbanController");
    var ListController = require("web.ListController");
    var CalendarController = require("web.CalendarController");

    var IncludeCustomButtonsView = {
        renderButtons: function ($node) {
            this._super.apply(this, arguments);

            if (this.$buttons && this.modelMatches()) {
                this.tryToAppendCustomButton();
            }
        },

        modelMatches: function() {
            return this.modelName == 'facility.facility' ||
                   this.modelName == 'facility.reservation';
        },

        tryToAppendCustomButton: function() {
            let template = false;
            let selector = false;

            switch(this.viewType) {
                case 'list':
                    template = 'CalendarView.buttons.search_available_facility';
                    selector = 'button:last';
                    this.appendCustomButton(selector, template);
                    break;

                case 'kanban':
                    template = 'CalendarView.buttons.search_available_facility';
                    selector = 'button:last';
                    this.appendCustomButton(selector, template);
                    break;

                case 'calendar':
                    template = 'CalendarView.buttons.search_available_facility';
                    selector = '> div.btn-group:last';
                    this.appendCustomButton(selector, template);
                    break;
            } // switch
        },

        appendCustomButton: function(selector, template) {
            let element = this.$buttons.find(selector);
            let custom = null;

            if(element.length === 1) {
                custom = $(QWeb.render(template));
                custom = element.after(custom);

                this.listenForClickEvent();
            }

            return custom;
        },

        listenForClickEvent: function(event) {
            let selector = '#EB40E9ABF36F47739DB909F26B9A857B';
            let button = this.$buttons.find(selector);

            button.on('click', this.proxy('showFacilityWizard'));
        },

        showFacilityWizard: function(event) {

            var action = {
                type: "ir.actions.act_window",
                name: "Search available",
                res_model: "facility.search.available.wizard",
                views: [[false,'form']],
                target: 'new',
                views: [[false, 'form']],
                view_type : 'form',
                view_mode : 'form',
                context: this.initialState.context,
                flags: {'form': {'action_buttons': true, 'options': {'mode': 'edit'}}}
            };

            return this.do_action(action);
        },

    };

    KanbanController.include(IncludeCustomButtonsView);
    ListController.include(IncludeCustomButtonsView);
    CalendarController.include(IncludeCustomButtonsView);

});