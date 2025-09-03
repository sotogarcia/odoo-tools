/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

const cogMenuRegistry = registry.category("cogMenu");

export class FacilityCogMenu extends Component {
    static template = "facility_management.CogMenuItem";
    static components = { DropdownItem };
    static props = {
        config: { type: Object, optional: true },
        close: { type: Function, optional: true },
    };
    onClick() {
        console.log("OK!");
        this.props?.close?.();
    }
}

const ALLOWED_VIEWS = new Set(["list", "kanban", "calendar"]);
const ALLOWED_MODELS = new Set(["facility.facility", "facility.reservation"]);

// Caché simple: actionId -> res_model
const actionModelCache = new Map();

async function getResModel(env) {
    // 1) Fuentes rápidas (si existen)
    const rm =
        env?.model?.root?.resModel ||
        env?.config?.resModel ||
        env?.config?.model ||
        env?.config?.action?.res_model ||
        env?.config?.context?.active_model ||
        null;
    if (rm) return rm;

    // 2) Fuente 100% fiable: leer el act_window
    const actionId = env?.config?.actionId;
    if (!(env?.config?.actionType === "ir.actions.act_window" && actionId)) {
        return null;
    }
    if (actionModelCache.has(actionId)) {
        return actionModelCache.get(actionId);
    }

    // Leer sólo el campo res_model del act_window
    // Nota: 'orm' está disponible vía env.services.orm
    const res = await env.services.orm.call(
        "ir.actions.act_window",
        "read",
        [[actionId], ["res_model"]]
    );
    const resModel = (res && res[0] && res[0].res_model) || null;
    actionModelCache.set(actionId, resModel);
    return resModel;
}

export const FacilityCogMenuItem = {
    Component: FacilityCogMenu,
    groupNumber: 20,
    isDisplayed: async (env) => {
        const { config } = env;

        // Solo para acciones window en vistas permitidas
        if (!(config?.actionType === "ir.actions.act_window" && config?.actionId)) {
            return false;
        }
        if (!ALLOWED_VIEWS.has(config?.viewType)) {
            return false;
        }

        // Modelo fiable (con fallback a lectura del act_window)
        const rm = await getResModel(env);
        return rm ? ALLOWED_MODELS.has(rm) : false;
    },
};

cogMenuRegistry.add("facility-cog-menu", FacilityCogMenuItem, { sequence: 10 });
