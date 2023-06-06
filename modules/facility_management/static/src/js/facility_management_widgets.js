odoo.define('facility_management.facility_next_time_widget', function (require) {
    "use strict";

    var AbstractField = require('web.AbstractField');
    var core = require('web.core');
    var fieldRegistry = require('web.field_registry');
    var QWeb = core.qweb;
    var time = require('web.time');

    var FacilityFieldNextTime = AbstractField.extend({
        className: 'o_facility_next_time',

        _render: function () {
            let date_str = false;
            let date_value = false
            let date_icon = 'fa-ellipsis-h';
            let next_time = this._tz_value();

            if (next_time) {
                date_value = next_time.format(
                    time.getLangDatetimeFormat(next_time));

                if (this._isToday(next_time)) {
                    let format = time.getLangTimeFormat(next_time);
                    date_str = next_time.format(format);
                    date_icon = 'fa-clock-o';
                } else {
                    let format = time.getLangDateFormat(next_time);
                    date_str = next_time.format(format);
                    date_icon = 'fa-calendar';
                }
            }

            this.$el.html(QWeb.render('next_time_value', {
                DateTimeStr: date_str,
                DateTimeIcon: date_icon,
                DateTimeValue: date_value
            }));

            if('class' in this.attrs) {
                this.$el.addClass(this.attrs.class);
            }
        },

        _tz_value() {
            if (this.value) {
                let offset = this.getSession().getTZOffset(this.value);
                return this.value.clone().add(offset, 'minutes');
            } else {
                return this.value;
            }
        },

        _isToday: function(someDate) {
            const today = new Date()

            return someDate.date() == today.getDate() &&
            someDate.month() == today.getMonth() &&
            someDate.year() == today.getFullYear()
        }

    });

    fieldRegistry.add('facility_next_time', FacilityFieldNextTime);

    return FacilityFieldNextTime;
});

odoo.define('facility_management.facility_users_widget', function (require) {
    "use strict";

    var AbstractField = require('web.AbstractField');
    var core = require('web.core');
    var fieldRegistry = require('web.field_registry');
    var QWeb = core.qweb;
    var time = require('web.time');
    var translation = require('web.translation');

    var _t = translation._t;

    var FacilityUsers = AbstractField.extend({
        className: 'o_facility_users',

        _render: function () {
            let users = false;
            let users_icon = false;
            let value = this.value;

            if (this._hasUsers(value)) {
                users = `${value} ${_t('seats')}`;
                users_icon = 'fa-users';
            } else {
                users = _t('Equipment');
                users_icon = 'fa-desktop';
            }

            this.$el.html(QWeb.render('facility_users', {
                UsersValue: users,
                UsersIcon: users_icon
            }));

            if('class' in this.attrs) {
                this.$el.addClass(this.attrs.class);
            }
        },

        /**
         * This method checks if the value is for display or not.
         *
         * The widget can display the number of users given as a number or as a
         * string. In the first case the value must be greater than zero and in
         * the second a non-empty string. In any other case, it will not show
         * anything.
         */
        _hasUsers: function(value) {
            let num = (typeof(value) == 'number' && value > 0)
            let str =  (typeof(value) == 'string' && value.length > 0)

            return num || str
        },

    });

    fieldRegistry.add('facility_users', FacilityUsers);

    return FacilityUsers;
});


/**
 * Following widget prevents the form Dialog will be opened when user clicks
 * on many2many record row.
 */
odoo.define('facility_management.many2many_frozen', function (require) {
    "use strict";

    var fieldRegistry = require('web.field_registry');
    var relationalFields = require('web.relational_fields');
    var FieldMany2Many = relationalFields.FieldMany2Many;

    var Many2ManyFrozen = FieldMany2Many.extend({

        _onOpenRecord: function (event) {
            event.stopPropagation();
        },

    });

    fieldRegistry.add('many2many_frozen', Many2ManyFrozen);

    return Many2ManyFrozen;
});

