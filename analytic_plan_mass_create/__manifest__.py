# Copyright 2023 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Analytic Plan Mass Create",
    "version": "14.0.1.0.0",
    "author": "ForgeFlow",
    "website": "https://github.com/forgeflow/project-bid",
    "category": "Generic Modules/Projects & Services",
    "summary": """Analytic Plan Mass Create""",
    "license": "AGPL-3",
    "depends": ["analytic_plan", "account"],
    "data": [
        "security/ir.model.access.csv",
        "views/analytic_plan_mass_create_template_view.xml",
        "wizard/analytic_plan_mass_create_view.xml",
    ],
    "installable": True,
}
