/* Copyright (C)
 * Facility Management - field widgets (Odoo 18)
 */
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { _t } from "@web/core/l10n/translation";
import {
  formatDate,
  formatTime,
  formatDateTime,
} from "@web/core/l10n/dates";

class FacilityNextTimeField extends Component {
  static template = "facility_management.FacilityNextTime";
  static props = { ...standardFieldProps };

  get computed() {
    const v = this.props.value;
    if (!v) {
      return { label: null, icon: "fa-ellipsis-h", title: null };
    }
    const title = formatDateTime(this.env, v);
    const sameDay =
      formatDate(this.env, v) === formatDate(this.env, new Date());
    return {
      label: sameDay ? formatTime(this.env, v) : formatDate(this.env, v),
      icon: sameDay ? "fa-clock-o" : "fa-calendar",
      title,
    };
  }
}

class FacilityUsersField extends Component {
  static template = "facility_management.FacilityUsers";
  static props = { ...standardFieldProps };

  get users() {
    const v = this.props.value;
    const hasNum = typeof v === "number" && v > 0;
    const hasStr = typeof v === "string" && v.length > 0;
    if (hasNum || hasStr) {
      return { label: `${v} ${_t("seats")}`, icon: "fa-users" };
    }
    return { label: _t("Equipment"), icon: "fa-desktop" };
  }
}

registry.category("fields").add("facility_next_time", {
  component: FacilityNextTimeField,
  supportedTypes: ["datetime"],
});

registry.category("fields").add("facility_users", {
  component: FacilityUsersField,
  supportedTypes: ["integer", "char"],
});
