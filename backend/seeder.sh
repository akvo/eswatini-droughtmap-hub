#!/usr/bin/env bash

echo "Seed Administration? [y/n]"
read -r seed_administration
if [[ "${seed_administration}" == 'y' || "${seed_administration}" == 'Y' ]]; then
    python manage.py generate_administrations_seeder
fi

echo "Seed Role and Abilities? [y/n]"
read -r seed_role_abilities
if [[ "${seed_role_abilities}" == 'y' || "${seed_role_abilities}" == 'Y' ]]; then
    python manage.py generate_roles_n_abilities_seeder
fi

echo "Add New Super Admin? [y/n]"
read -r add_account
if [[ "${add_account}" == 'y' || "${add_account}" == 'Y' ]]; then
    echo "Please type email address"
    read -r email_address
    if [[ "${email_address}" != '' ]]; then
        python manage.py createsuperuser --email "${email_address}" --role 1
    fi
fi

echo "Seed Fake User? [y/n]"
read -r fake_user
if [[ "${fake_user}" == 'y' || "${fake_user}" == 'Y' ]]; then
    python manage.py generate_admin_seeder
    python manage.py fake_users_seeder
fi

# Everything the National overview and the Detailed Insights tabs read, in
# dependency order. Idempotent, so answering 'y' after the prompts above is
# harmless — seed_demo re-runs those same seeders.
echo "Seed Demo Data (National overview + Detailed insights)? [y/n]"
read -r seed_demo
if [[ "${seed_demo}" == 'y' || "${seed_demo}" == 'Y' ]]; then
    echo "Path to a local CDI GeoTIFF archive for REAL values (optional)."
    echo "e.g. ./storage/geotiffs — leave blank for GeoNode/synthetic:"
    read -r geotiffs_path
    if [[ "${geotiffs_path}" != '' ]]; then
        python manage.py seed_demo --path "${geotiffs_path}"
    else
        python manage.py seed_demo
    fi
fi

python manage.py generate_config
