# Migración

## Pasos preliminares

- [x] Cambiar version to 18.0.1.0.0
- [-] Cambiar año de copyright a 2025
- [x] ``<path_to_odoo>/odoo-bin upgrade_code --addons-path /ruta/a/tus_addons --from 17.0 --to 18.0``
 
## Odoo 13 → 14

- [x] Eliminar `@api.one` y `@api.multi`; usar `ensure_one()` cuando proceda.
- [x] Sustituir `@api.model_cr` si existe.
- [x] Evitar dominios en `onchange`; mover filtrado a vistas/campos.
- [x] Ver que se hace con @api.model_create_multi

## Odoo 14 → 15

- [x] Definir *assets* en `__manifest__.py` (bundles QWeb/JS/CSS).
- [x] Migrar plantillas de email de Jinja a QWeb.
- [x] Adoptar OWL y módulos ES; renombrar a `*.esm.js` cuando aplique.

## Odoo 15 → 16

- [x] Revisar APIs de *flush*/*invalidate* en el ORM.
- [x] Actualizar firmas de `_read_group` en overrides y tests.

## Odoo 16 → 17

- [ ] Reemplazar `attrs`/`states` por expresiones directas en atributos.
  - [ ] v16: `attrs="{'invisible': [('state','=','done')]}"`.
  - [ ] v17: `invisible="state == 'done'"`.
- [x] Usar `column_invisible` en listas en lugar de `invisible`.
- [x] Considerar `search_fetch()` y `fetch()` en lugar de `search_read`.

## Odoo 17 → 18

- [x] Reemplazar `user_has_groups` por `self.env.user.has_group()`/`has_groups()`.
- [x] Unificar acceso: usar `check_access()` en lugar de `check_access_*`.
- [x] Reemplazar `_name_search` por `_search_display_name`.
- [x] Importar `Registry` de `odoo.modules.registry`; usar `Registry(db_name)`.
- [x] Considerar `self.env._('...')` en lugar de `_('...')`.
- [x] Limpiar vistas: autoañadir campos invisibles en dominios/atributos.
- [x] Simplificar *chatter*: `<div class="oe_chatter">…</div>` → `<chatter />`.
- [x] Reemplazar `_filter_access_rule*` por `_filter_access()`.
- [x] Reemplazar `_check_recursion()` por `_has_cycle()`.
- [-] Revisar `copy`/`copy_data` en *multi-recordsets*
  (p. ej., `copy_data` devuelve lista).
- [x] Reemplazar `group_operator` por `aggregator` en definiciones de campos.
- [-] Vigilar búsquedas en `related` no almacenados: lanzar excepción.
- [x] Valorar `search_fetch()` si `search()` no se ejecuta siempre.
- [-] Definir *field path* en `ir.actions.act_window` para URLs más limpias.
- [x] Retirar `/** @odoo-module **/` en JS si no es necesario.
- [-] En tours JS, sustituir `extra_trigger` por un paso independiente.

## Revisiones finales
- [x] Comprobar logs y reparar posibles errores
- [x] Traducir
    1. Exportar traducción y completar en PoEdit
    2. Dar la traducción a ChatGPT para que busque errores y corregir estos   
- [ ] Revisar lista TODO 
       · El JS del botón debe comprobar los permisos
       · Icono al JS


```
┌──────────────────────────┐
│ name                     │
│ __Dirección__            │
│ Telefono: ___ Email: ___ │
│ Responsable: ___         │
└──────────────────────────┘
```

facility_count
manager_id
