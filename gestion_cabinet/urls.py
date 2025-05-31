from django.urls import path
from . import views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # Authentication
    path('login/', auth_views.LoginView.as_view(template_name='gestion_cabinet/login.html'), name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.UserCreateView.as_view(), name='register'),
    path('profile/', views.profile_view, name='profile'),
    
    # Gestion des patients
    path('patients/', views.patient_list, name='patient_list'),
    path('patients/<int:patient_id>/', views.patient_detail, name='patient_detail'),
    
    # Gestion des secrétaires (réservé aux dentistes)
    path('secretaires/', views.secretaire_list, name='secretaire_list'),
    path('secretaires/nouveau/', views.secretaire_create, name='secretaire_create'),
    path('secretaires/<int:pk>/modifier/', views.secretaire_update, name='secretaire_update'),
    path('secretaires/<int:pk>/supprimer/', views.secretaire_delete, name='secretaire_delete'),
    
    # Rendez-vous
    path('rendez-vous/', views.rendez_vous_list, name='rendez_vous_list'),
    path('rendez-vous/nouveau/', views.rendez_vous_create, name='rendez_vous_create'),
    path('rendez_vous/<int:rdv_id>/annuler/', views.rendez_vous_annuler, name='rendez_vous_annuler'),
    path('rendez_vous/<int:rdv_id>/payer/', views.marquer_rdv_paye, name='marquer_rdv_paye'),
    path('rendez_vous/<int:rdv_id>/montant/', views.definir_montant_rdv, name='definir_montant_rdv'),
    
    # Consultations
    path('consultation/nouveau/<int:rendez_vous_id>/', views.consultation_create, name='consultation_create'),
    path('consultation/<int:pk>/', views.consultation_detail, name='consultation_detail'),
    path('consultation/<int:pk>/modifier/', views.consultation_update, name='consultation_update'),
    
    # Factures
    path('facture/nouveau/<int:consultation_id>/', views.facture_create, name='facture_create'),
    path('facture/<int:pk>/', views.facture_detail, name='facture_detail'),
    path('facture/<int:pk>/payer/', views.facture_payer, name='facture_payer'),
    
    # Stock
    path('stock/', views.stock_list, name='stock_list'),
    path('stock/produit/nouveau/', views.stock_create, name='stock_create'),
    path('stock/produit/<int:pk>/modifier/', views.stock_update, name='stock_update'),
    path('stock/produit/<int:pk>/supprimer/', views.stock_delete, name='stock_delete'),
    
    # Mouvements de stock
    path('stock/mouvement/nouveau/', views.mouvement_stock_create, name='mouvement_stock_create'),
    
    # Paiements
    path('paiement/<int:facture_id>/initier/', views.initier_paiement, name='initier_paiement'),
    path('paiement/<int:facture_id>/cb/', views.process_paiement_cb, name='process_paiement_cb'),
    path('paiement/<int:facture_id>/especes/', views.process_paiement_especes, name='process_paiement_especes'),
    path('paiement/<int:facture_id>/success/', views.paiement_success, name='paiement_success'),
] 