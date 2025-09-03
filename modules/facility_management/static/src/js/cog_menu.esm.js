// -----------------------------------------------------------------------------
// Facility Cog Menu Action (Odoo 18, ESM)
// -----------------------------------------------------------------------------
// Purpose:
//   Add a cog menu entry that opens the transient wizard
//   "facility.search.available.wizard" as a modal (target: "new").
//
// Scope:
//   - Shown only on list/kanban/calendar views.
//   - Shown only for the allowed models (see ALLOWED_MODELS).
//
// Notes:
//   - This is an ESM module (no `/** @odoo-module **/` header).
//   - The item is registered in the "cogMenu" registry.
//   - It relies on the Action service to open the wizard.
//   - The current view context is read from `env.searchModel.context`.
//
// -----------------------------------------------------------------------------

import { _t } from "@web/core/l10n/translation";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

// -----------------------------------------------------------------------------
// Registry category
// -----------------------------------------------------------------------------
const cogMenuRegistry = registry.category("cogMenu");

// -----------------------------------------------------------------------------
// Component: FacilityCogMenu
// -----------------------------------------------------------------------------
// Renders a dropdown item inside the cog menu. When clicked, it uses the
// Action service to open the target wizard in a modal dialog.
// -----------------------------------------------------------------------------
export class FacilityCogMenu extends Component {
    // QWeb template for this item (must exist in your module XML).
    static template = "facility_management.CogMenuItem";

    // Child components used by this item.
    static components = {
        DropdownItem
    };

    // Props provided by the cog menu infrastructure:
    // - `config`: view context and metadata (optional).
    // - `close`: function to close the dropdown (optional).
    static props = {
        config: {
            type: Object,
            optional: true
        },
        close: {
            type: Function,
            optional: true
        },
    };

    // -------------------------------------------------------------------------
    // Event handlers
    // -------------------------------------------------------------------------
    /**
     * Handle the click on the cog menu item:
     * - Resolve Action service.
     * - Obtain the active model (if needed in the future).
     * - Obtain the current view context from SearchModel (if present).
     * - Open the wizard as a modal (target: "new").
     * - Close the dropdown afterward.
     */
    onClick() {
        const actionService = this.env.services.action;

        // Active model is not strictly needed to open the wizard, but we keep
        // it available for future logic or assertions.
        const resModel =
            this.env?.searchModel?.resModel || this.props?.config?.resModel;

        // Use the current search model context when present. This allows the
        // wizard to inherit useful keys (e.g., active_id, active_model, etc.).
        const ctx = (this.env?.searchModel && this.env.searchModel
            .context) || {};

        actionService.doAction({
            type: "ir.actions.act_window",
            name: _t("Search available"),
            res_model: "facility.search.available.wizard",
            view_mode: "form",
            views: [
                [false, "form"]
            ],
            target: "new",   // open as modal dialog
            context: ctx,    // pass current view context
        });

        this.props?.close?.(); // close the menu
    }
}

// -----------------------------------------------------------------------------
// Visibility rules
// -----------------------------------------------------------------------------
// Limit the cog menu item to specific view types and models.
// -----------------------------------------------------------------------------
const ALLOWED_VIEWS = new Set(["list", "kanban", "calendar"]);
const ALLOWED_MODELS = new Set(["facility.facility", "facility.reservation"]);

// -----------------------------------------------------------------------------
// Registry item definition
// -----------------------------------------------------------------------------
// - `isDisplayed` controls whether the item is shown for the current view.
// - `groupNumber` decides the logical group where the item is placed.
// -----------------------------------------------------------------------------
export const FacilityCogMenuItem = {
    Component: FacilityCogMenu,
    groupNumber: 20,
    isDisplayed: (env) => {
        const {
            config
        } = env;

        // Only for act_window actions (standard record views).
        if (!(config?.actionType === "ir.actions.act_window" && config
                ?.actionId)) {
            return false;
        }

        // Enforce allowed view types.
        if (!ALLOWED_VIEWS.has(config?.viewType)) {
            return false;
        }

        // Enforce allowed models.
        const rm = env.searchModel?.resModel;
        return rm ? ALLOWED_MODELS.has(rm) : false;
    },
};

// -----------------------------------------------------------------------------
// Registration
// -----------------------------------------------------------------------------
// Finally, register the item in the cog menu registry so it becomes available
// in eligible views.
// -----------------------------------------------------------------------------
cogMenuRegistry.add("facility-cog-menu", FacilityCogMenuItem, {
    sequence: 10
});
