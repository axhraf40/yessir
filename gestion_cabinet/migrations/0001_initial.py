from django.db import migrations, models
import django.contrib.auth.models
import django.contrib.auth.validators
import django.db.models.deletion
import django.utils.timezone

class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomUser',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('is_superuser', models.BooleanField(default=False, help_text='Designates that this user has all permissions without explicitly assigning them.', verbose_name='superuser status')),
                ('username', models.CharField(error_messages={'unique': 'A user with that username already exists.'}, help_text='Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only.', max_length=150, unique=True, validators=[django.contrib.auth.validators.UnicodeUsernameValidator()], verbose_name='username')),
                ('first_name', models.CharField(blank=True, max_length=150, verbose_name='first name')),
                ('last_name', models.CharField(blank=True, max_length=150, verbose_name='last name')),
                ('email', models.EmailField(blank=True, max_length=254, verbose_name='email address')),
                ('is_staff', models.BooleanField(default=False, help_text='Designates whether the user can log into this admin site.', verbose_name='staff status')),
                ('is_active', models.BooleanField(default=True, help_text='Designates whether this user should be treated as active. Unselect this instead of deleting accounts.', verbose_name='active')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now, verbose_name='date joined')),
                ('role', models.CharField(choices=[('PATIENT', 'Patient'), ('DENTISTE', 'Dentiste'), ('SECRETAIRE', 'Secrétaire')], max_length=20)),
                ('date_naissance', models.DateField(blank=True, null=True)),
                ('telephone', models.CharField(blank=True, max_length=15, null=True)),
                ('adresse', models.TextField(blank=True, null=True)),
                ('groups', models.ManyToManyField(blank=True, help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='custom_user_set', related_query_name='user', to='auth.group', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(blank=True, help_text='Specific permissions for this user.', related_name='custom_user_set', related_query_name='user', to='auth.permission', verbose_name='user permissions')),
            ],
            options={
                'db_table': 'auth_custom_user',
                'verbose_name': 'Utilisateur',
                'verbose_name_plural': 'Utilisateurs',
            },
            managers=[
                ('objects', django.contrib.auth.models.UserManager()),
            ],
        ),
        migrations.CreateModel(
            name='Dentiste',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('specialite', models.CharField(max_length=100)),
                ('telephone', models.CharField(max_length=15)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='dentiste_profile', to='gestion_cabinet.customuser')),
            ],
            options={
                'db_table': 'cabinet_dentiste',
            },
        ),
        migrations.CreateModel(
            name='Patient',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_naissance', models.DateField()),
                ('telephone', models.CharField(max_length=15)),
                ('adresse', models.TextField()),
                ('date_inscription', models.DateTimeField(auto_now_add=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='patient_profile', to='gestion_cabinet.customuser')),
            ],
            options={
                'db_table': 'cabinet_patient',
            },
        ),
        migrations.CreateModel(
            name='Secretaire',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('telephone', models.CharField(max_length=15)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='secretaire_profile', to='gestion_cabinet.customuser')),
            ],
            options={
                'db_table': 'cabinet_secretaire',
            },
        ),
        migrations.CreateModel(
            name='RendezVous',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_heure', models.DateTimeField()),
                ('motif', models.CharField(max_length=200)),
                ('statut', models.CharField(choices=[('PROGRAMME', 'Programmé'), ('EN_COURS', 'En cours'), ('TERMINE', 'Terminé'), ('ANNULE', 'Annulé')], default='PROGRAMME', max_length=20)),
                ('notes', models.TextField(blank=True)),
                ('dentiste', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gestion_cabinet.dentiste')),
                ('patient', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gestion_cabinet.patient')),
            ],
            options={
                'db_table': 'cabinet_rendez_vous',
                'verbose_name': 'Rendez-vous',
                'verbose_name_plural': 'Rendez-vous',
                'ordering': ['-date_heure'],
            },
        ),
        migrations.CreateModel(
            name='Consultation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('diagnostic', models.TextField()),
                ('traitement', models.TextField()),
                ('date_consultation', models.DateTimeField(auto_now_add=True)),
                ('rendez_vous', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='gestion_cabinet.rendezvous')),
            ],
        ),
        migrations.CreateModel(
            name='Facture',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('montant', models.DecimalField(decimal_places=2, max_digits=10)),
                ('date_emission', models.DateTimeField(auto_now_add=True)),
                ('statut', models.CharField(choices=[('EN_ATTENTE', 'En attente'), ('PAYE', 'Payé'), ('ECHEC', 'Échec de paiement')], default='EN_ATTENTE', max_length=20)),
                ('mode_paiement', models.CharField(blank=True, choices=[('CB', 'Carte bancaire'), ('ESPECES', 'Espèces')], max_length=20, null=True)),
                ('date_paiement', models.DateTimeField(blank=True, null=True)),
                ('reference_transaction', models.CharField(blank=True, max_length=100, null=True)),
                ('consultation', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='gestion_cabinet.consultation')),
            ],
        ),
        migrations.CreateModel(
            name='Produit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nom', models.CharField(max_length=200)),
                ('description', models.TextField()),
                ('quantite', models.IntegerField()),
                ('seuil_alerte', models.IntegerField()),
                ('prix_unitaire', models.DecimalField(decimal_places=2, max_digits=10)),
            ],
        ),
        migrations.CreateModel(
            name='MouvementStock',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('type_mouvement', models.CharField(choices=[('ENTREE', 'Entrée'), ('SORTIE', 'Sortie')], max_length=10)),
                ('quantite', models.IntegerField()),
                ('date_mouvement', models.DateTimeField(auto_now_add=True)),
                ('effectue_par', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='gestion_cabinet.customuser')),
                ('produit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gestion_cabinet.produit')),
            ],
        ),
    ]