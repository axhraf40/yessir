from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib import messages
from django.urls import reverse_lazy
from django.utils import timezone
from .models import *
from .forms import *
from .decorators import patient_required, dentiste_required, secretaire_required, role_required
import stripe
from django.conf import settings
from django.db import models
from datetime import datetime, time
from django.contrib.auth import logout

def home(request):
    return render(request, 'gestion_cabinet/home.html')

@login_required
def dashboard(request):
    user = request.user
    context = {}
    
    if hasattr(user, 'patient_profile'):
        # Récupérer tous les rendez-vous du patient, triés par date
        context['rendez_vous'] = RendezVous.objects.filter(
            patient=user.patient_profile
        ).order_by('date_heure')
        
        # Récupérer toutes les consultations du patient
        context['consultations'] = Consultation.objects.filter(
            rendez_vous__patient=user.patient_profile
        ).order_by('-date_consultation')
        
        # Récupérer tous les rendez-vous avec un montant défini comme "factures"
        context['factures'] = RendezVous.objects.filter(
            patient=user.patient_profile,
            montant__gt=0  # Montant supérieur à 0
        ).order_by('-date_heure')
        
        return render(request, 'gestion_cabinet/dashboard_patient.html', context)
    
    elif hasattr(user, 'dentiste_profile'):
        # Debug information
        print(f"User Role: {user.role}")
        print(f"User ID: {user.id}")
        print(f"Dentiste Profile: {user.dentiste_profile}")
        
        # Get today's date range
        today = timezone.now().date()
        today_start = timezone.make_aware(datetime.combine(today, time.min))
        today_end = timezone.make_aware(datetime.combine(today, time.max))
        
        context['rendez_vous_aujourdhui'] = RendezVous.objects.filter(
            dentiste=user.dentiste_profile,
            date_heure__range=(today_start, today_end)
        ).order_by('date_heure')
        
        context['consultations'] = Consultation.objects.filter(
            rendez_vous__dentiste=user.dentiste_profile
        ).order_by('-date_consultation')
        
        context['secretaires'] = Secretaire.objects.all()
        return render(request, 'gestion_cabinet/dashboard_dentiste.html', context)
    
    elif hasattr(user, 'secretaire_profile'):
        # Get today's date range
        today = timezone.now().date()
        today_start = timezone.make_aware(datetime.combine(today, time.min))
        today_end = timezone.make_aware(datetime.combine(today, time.max))
        
        context['rendez_vous_aujourdhui'] = RendezVous.objects.filter(
            date_heure__range=(today_start, today_end)
        ).order_by('date_heure')
        
        context['produits_stock_faible'] = Produit.objects.filter(
            quantite__lte=models.F('seuil_alerte')
        )
        return render(request, 'gestion_cabinet/dashboard_secretaire.html', context)
    
    messages.error(request, "Votre compte n'est pas correctement configuré. Veuillez contacter l'administrateur.")
    return redirect('home')

class UserCreateView(CreateView):
    form_class = UserRegistrationForm
    template_name = 'gestion_cabinet/patient_register.html'
    success_url = reverse_lazy('login')

    def form_valid(self, form):
        messages.success(self.request, 'Compte créé avec succès ! Vous pouvez maintenant vous connecter.')
        return super().form_valid(form)

@login_required
def rendez_vous_create(request):
    if request.method == 'POST':
        form = RendezVousPatientForm(request.POST)
        if form.is_valid():
            rendez_vous = form.save(commit=False)
            if hasattr(request.user, 'patient_profile'):
                rendez_vous.patient = request.user.patient_profile
            rendez_vous.statut_paiement = 'EN_ATTENTE'
            rendez_vous.montant = 0  # Montant initial à 0
            rendez_vous.save()
            messages.success(request, 'Rendez-vous créé avec succès !')
            return redirect('rendez_vous_list')
    else:
        form = RendezVousPatientForm()
    return render(request, 'gestion_cabinet/rendez_vous_form.html', {'form': form})

@login_required
def rendez_vous_list(request):
    user = request.user
    if hasattr(user, 'patient_profile'):
        rendez_vous = RendezVous.objects.filter(patient=user.patient_profile)
    elif hasattr(user, 'dentiste_profile'):
        rendez_vous = RendezVous.objects.filter(dentiste=user.dentiste_profile)
    elif hasattr(user, 'secretaire_profile'):
        rendez_vous = RendezVous.objects.all()
    else:
        rendez_vous = RendezVous.objects.none()
    
    return render(request, 'gestion_cabinet/rendez_vous_list.html', {'rendez_vous': rendez_vous})

@login_required
def rendez_vous_annuler(request, rdv_id):
    rendez_vous = get_object_or_404(RendezVous, id=rdv_id)
    
    # Vérifier les permissions
    if (hasattr(request.user, 'patient_profile') and request.user.patient_profile == rendez_vous.patient) or \
       (hasattr(request.user, 'secretaire_profile')):
        if rendez_vous.statut == 'PROGRAMME':
            rendez_vous.statut = 'ANNULE'
            rendez_vous.save()
            messages.success(request, 'Le rendez-vous a été annulé avec succès.')
        else:
            messages.error(request, 'Ce rendez-vous ne peut pas être annulé.')
    else:
        messages.error(request, "Vous n'avez pas la permission d'annuler ce rendez-vous.")
    
    return redirect('rendez_vous_list')

@login_required
@dentiste_required
def consultation_create(request, rendez_vous_id):
    rendez_vous = get_object_or_404(RendezVous, id=rendez_vous_id, dentiste=request.user.dentiste_profile)
    
    if request.method == 'POST':
        form = ConsultationForm(request.POST)
        if form.is_valid():
            consultation = form.save(commit=False)
            consultation.rendez_vous = rendez_vous
            consultation.save()
            rendez_vous.statut = 'TERMINE'
            rendez_vous.save()
            
            messages.success(request, 'Consultation enregistrée avec succès !')
            return redirect('consultation_detail', pk=consultation.pk)
    else:
        form = ConsultationForm()
    
    historique_consultations = Consultation.objects.filter(
        rendez_vous__patient=rendez_vous.patient
    ).exclude(
        rendez_vous=rendez_vous
    ).order_by('-date_consultation')
    
    return render(request, 'gestion_cabinet/consultation_form.html', {
        'form': form,
        'rendez_vous': rendez_vous,
        'historique_consultations': historique_consultations
    })

@login_required
def consultation_detail(request, pk):
    consultation = get_object_or_404(Consultation, pk=pk)
    if hasattr(request.user, 'patient_profile'):
        if request.user.patient_profile != consultation.rendez_vous.patient:
            messages.error(request, "Vous n'avez pas accès à cette consultation.")
            return redirect('dashboard')
    elif hasattr(request.user, 'dentiste_profile'):
        if request.user.dentiste_profile != consultation.rendez_vous.dentiste:
            messages.error(request, "Vous n'avez pas accès à cette consultation.")
            return redirect('dashboard')
    elif not hasattr(request.user, 'secretaire_profile'):
        messages.error(request, "Vous n'avez pas accès à cette consultation.")
        return redirect('dashboard')
    
    return render(request, 'gestion_cabinet/consultation_detail.html', {'consultation': consultation})

@login_required
@secretaire_required
def facture_create(request, consultation_id):
    consultation = get_object_or_404(Consultation, id=consultation_id)
    
    if request.method == 'POST':
        form = FactureForm(request.POST)
        if form.is_valid():
            facture = form.save(commit=False)
            facture.consultation = consultation
            facture.save()
            messages.success(request, 'Facture créée avec succès !')
            return redirect('facture_detail', pk=facture.pk)
    else:
        form = FactureForm()
    
    return render(request, 'gestion_cabinet/facture_form.html', {
        'form': form,
        'consultation': consultation
    })

@login_required
def facture_detail(request, pk):
    facture = get_object_or_404(Facture, pk=pk)
    if hasattr(request.user, 'patient_profile'):
        if request.user.patient_profile != facture.consultation.rendez_vous.patient:
            messages.error(request, "Vous n'avez pas accès à cette facture.")
            return redirect('dashboard')
    elif not (hasattr(request.user, 'secretaire_profile') or hasattr(request.user, 'dentiste_profile')):
        messages.error(request, "Vous n'avez pas accès à cette facture.")
        return redirect('dashboard')
    
    return render(request, 'gestion_cabinet/facture_detail.html', {'facture': facture})

@login_required
def stock_list(request):
    if not (hasattr(request.user, 'dentiste_profile') or hasattr(request.user, 'secretaire_profile')):
        messages.error(request, "Vous n'avez pas accès à la gestion du stock.")
        return redirect('dashboard')
    
    produits = Produit.objects.all()
    return render(request, 'gestion_cabinet/stock_list.html', {'produits': produits})

@login_required
def mouvement_stock_create(request):
    if not (hasattr(request.user, 'secretaire_profile') or hasattr(request.user, 'dentiste_profile')):
        messages.error(request, "Vous n'avez pas accès à la gestion du stock.")
        return redirect('dashboard')

    produit_id = request.GET.get('produit')
    type_mouvement = request.GET.get('type', 'ENTREE')
    produit = None
    
    if produit_id:
        produit = get_object_or_404(Produit, id=produit_id)

    if request.method == 'POST':
        form = MouvementStockForm(request.POST)
        if form.is_valid():
            mouvement = form.save(commit=False)
            mouvement.effectue_par = request.user
            mouvement.type_mouvement = request.POST.get('type_mouvement', 'ENTREE')
            
            # Vérifier si le stock est suffisant pour une sortie
            if mouvement.type_mouvement == 'SORTIE' and mouvement.produit.quantite < mouvement.quantite:
                messages.error(request, 'Stock insuffisant !')
                return redirect('mouvement_stock_create')
            
            # Mettre à jour la quantité du produit
            if mouvement.type_mouvement == 'ENTREE':
                mouvement.produit.quantite += mouvement.quantite
            else:
                mouvement.produit.quantite -= mouvement.quantite
            
            mouvement.produit.save()
            mouvement.save()
            
            messages.success(request, 'Mouvement de stock enregistré avec succès !')
            return redirect('stock_list')
    else:
        initial = {}
        if produit_id:
            initial['produit'] = produit_id
        form = MouvementStockForm(initial=initial)

    context = {
        'form': form,
        'produit': produit,
        'type_mouvement': type_mouvement
    }
    return render(request, 'gestion_cabinet/mouvement_stock_form.html', context)

@login_required
def stock_create(request):
    if not (hasattr(request.user, 'secretaire_profile') or hasattr(request.user, 'dentiste_profile')):
        messages.error(request, "Vous n'avez pas accès à la gestion du stock.")
        return redirect('dashboard')

    if request.method == 'POST':
        form = ProduitForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Produit ajouté avec succès!')
            return redirect('stock_list')
    else:
        form = ProduitForm()
    return render(request, 'gestion_cabinet/stock_form.html', {'form': form, 'action': 'create'})

@login_required
def stock_update(request, pk):
    if not (hasattr(request.user, 'secretaire_profile') or hasattr(request.user, 'dentiste_profile')):
        messages.error(request, "Vous n'avez pas accès à la gestion du stock.")
        return redirect('dashboard')

    produit = get_object_or_404(Produit, pk=pk)
    if request.method == 'POST':
        form = ProduitForm(request.POST, instance=produit)
        if form.is_valid():
            form.save()
            messages.success(request, 'Produit mis à jour avec succès!')
            return redirect('stock_list')
    else:
        form = ProduitForm(instance=produit)
    return render(request, 'gestion_cabinet/stock_form.html', {'form': form, 'produit': produit, 'action': 'update'})

@login_required
def stock_delete(request, pk):
    if not (hasattr(request.user, 'secretaire_profile') or hasattr(request.user, 'dentiste_profile')):
        messages.error(request, "Vous n'avez pas accès à la gestion du stock.")
        return redirect('dashboard')

    produit = get_object_or_404(Produit, pk=pk)
    if request.method == 'POST':
        produit.delete()
        messages.success(request, 'Produit supprimé avec succès!')
        return redirect('stock_list')
    return render(request, 'gestion_cabinet/stock_confirm_delete.html', {'produit': produit})

@login_required
def patient_list(request):
    # Vérifier que l'utilisateur est soit dentiste soit secrétaire
    if not (hasattr(request.user, 'dentiste_profile') or hasattr(request.user, 'secretaire_profile')):
        messages.error(request, "Vous n'avez pas accès à la liste des patients.")
        return redirect('dashboard')
    
    # Récupérer le paramètre de recherche
    search_query = request.GET.get('q', '')
    
    # Filtrer les patients
    patients = Patient.objects.all()
    if search_query:
        patients = patients.filter(
            models.Q(user__first_name__icontains=search_query) |
            models.Q(user__last_name__icontains=search_query) |
            models.Q(telephone__icontains=search_query)
        )
    
    # Trier les patients par nom et prénom
    patients = patients.order_by('user__last_name', 'user__first_name')
    
    context = {
        'patients': patients,
        'search_query': search_query,
    }
    
    return render(request, 'gestion_cabinet/patient_list.html', context)

@login_required
@role_required(['DENTISTE', 'SECRETAIRE'])
def patient_detail(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    rendez_vous = RendezVous.objects.filter(patient=patient).order_by('-date_heure')
    consultations = Consultation.objects.filter(rendez_vous__patient=patient).order_by('-date_consultation')
    factures = Facture.objects.filter(consultation__rendez_vous__patient=patient).order_by('-date_emission')
    
    context = {
        'patient': patient,
        'rendez_vous': rendez_vous,
        'consultations': consultations,
        'factures': factures,
    }
    return render(request, 'gestion_cabinet/patient_detail.html', context)

@login_required
def facture_payer(request, pk):
    facture = get_object_or_404(Facture, pk=pk)
    
    if not hasattr(request.user, 'secretaire'):
        messages.error(request, "Vous n'avez pas la permission de modifier cette facture.")
        return redirect('facture_detail', pk=pk)
    
    if facture.statut != 'PAYE':
        facture.statut = 'PAYE'
        facture.date_paiement = timezone.now()
        facture.save()
        messages.success(request, 'La facture a été marquée comme payée.')
    
    return redirect('facture_detail', pk=pk)

@login_required
def initier_paiement(request, facture_id):
    facture = get_object_or_404(Facture, id=facture_id)
    
    # Vérifier que l'utilisateur est soit le patient concerné, soit une secrétaire
    if not (hasattr(request.user, 'secretaire') or 
            (hasattr(request.user, 'patient') and request.user.patient == facture.consultation.rendez_vous.patient)):
        messages.error(request, "Vous n'avez pas la permission d'accéder à cette facture.")
        return redirect('dashboard')
    
    return render(request, 'gestion_cabinet/initier_paiement.html', {
        'facture': facture
    })

@login_required
def process_paiement_cb(request, facture_id):
    facture = get_object_or_404(Facture, id=facture_id)
    
    if not (hasattr(request.user, 'secretaire') or 
            (hasattr(request.user, 'patient') and request.user.patient == facture.consultation.rendez_vous.patient)):
        messages.error(request, "Vous n'avez pas la permission d'accéder à cette facture.")
        return redirect('dashboard')

    stripe.api_key = settings.STRIPE_SECRET_KEY

    if request.method == 'POST':
        try:
            # Créer l'intention de paiement
            intent = stripe.PaymentIntent.create(
                amount=int(facture.montant * 100),  # Stripe utilise les centimes
                currency='eur',
                metadata={'facture_id': facture.id}
            )
            
            return render(request, 'gestion_cabinet/process_paiement_cb.html', {
                'facture': facture,
                'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
                'client_secret': intent.client_secret
            })
            
        except Exception as e:
            messages.error(request, "Une erreur est survenue lors de l'initialisation du paiement.")
            return redirect('facture_detail', facture_id=facture.id)
    
    return redirect('initier_paiement', facture_id=facture.id)

@login_required
def process_paiement_especes(request, facture_id):
    facture = get_object_or_404(Facture, id=facture_id)
    
    if not (hasattr(request.user, 'secretaire') or 
            (hasattr(request.user, 'patient') and request.user.patient == facture.consultation.rendez_vous.patient)):
        messages.error(request, "Vous n'avez pas la permission d'accéder à cette facture.")
        return redirect('dashboard')

    if request.method == 'POST':
        facture.mode_paiement = 'ESPECES'
        facture.statut = 'EN_ATTENTE'
        facture.save()
        messages.info(request, f"Veuillez préparer {facture.montant}€ en espèces pour votre prochain rendez-vous.")
        return redirect('facture_detail', facture_id=facture.id)
    
    return redirect('initier_paiement', facture_id=facture.id)

@login_required
def paiement_success(request, facture_id):
    facture = get_object_or_404(Facture, id=facture_id)
    
    if not (hasattr(request.user, 'secretaire') or 
            (hasattr(request.user, 'patient') and request.user.patient == facture.consultation.rendez_vous.patient)):
        messages.error(request, "Vous n'avez pas la permission d'accéder à cette facture.")
        return redirect('dashboard')

    facture.statut = 'PAYE'
    facture.date_paiement = timezone.now()
    facture.save()
    
    messages.success(request, "Paiement effectué avec succès !")
    return redirect('facture_detail', facture_id=facture.id)

class ProduitUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Produit
    form_class = ProduitForm
    template_name = 'gestion_cabinet/produit_form.html'
    success_url = reverse_lazy('stock_list')

    def test_func(self):
        return hasattr(self.request.user, 'secretaire')

    def form_valid(self, form):
        messages.success(self.request, 'Produit modifié avec succès !')
        return super().form_valid(form)

@login_required
def profile_view(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Votre profil a été mis à jour avec succès !')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    context = {
        'form': form,
        'user': request.user
    }
    return render(request, 'gestion_cabinet/profile.html', context)

# Gestion des secrétaires (réservé aux dentistes)
@login_required
def secretaire_list(request):
    if not hasattr(request.user, 'dentiste_profile'):
        messages.error(request, "Seuls les dentistes peuvent gérer les secrétaires.")
        return redirect('dashboard')
    
    secretaires = Secretaire.objects.all()
    return render(request, 'gestion_cabinet/secretaire_list.html', {'secretaires': secretaires})

@login_required
@dentiste_required
def secretaire_create(request):
    if request.method == 'POST':
        form = SecretaireRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Compte secrétaire créé avec succès!')
            return redirect('secretaire_list')
    else:
        form = SecretaireRegistrationForm()
    return render(request, 'gestion_cabinet/secretaire_form.html', {'form': form})

@login_required
def secretaire_update(request, pk):
    if not hasattr(request.user, 'dentiste_profile'):
        messages.error(request, "Seuls les dentistes peuvent modifier les secrétaires.")
        return redirect('dashboard')

    secretaire = get_object_or_404(Secretaire, pk=pk)
    if request.method == 'POST':
        form = SecretaireForm(request.POST, instance=secretaire)
        user_form = UserProfileForm(request.POST, request.FILES, instance=secretaire.user)
        if form.is_valid() and user_form.is_valid():
            form.save()
            user_form.save()
            messages.success(request, 'Compte secrétaire mis à jour avec succès!')
            return redirect('dashboard')
    else:
        form = SecretaireForm(instance=secretaire)
        user_form = UserProfileForm(instance=secretaire.user)
    return render(request, 'gestion_cabinet/secretaire_form.html', {
        'form': form,
        'user_form': user_form,
        'secretaire': secretaire
    })

@login_required
def secretaire_delete(request, pk):
    if not hasattr(request.user, 'dentiste_profile'):
        messages.error(request, "Seuls les dentistes peuvent supprimer des secrétaires.")
        return redirect('dashboard')

    secretaire = get_object_or_404(Secretaire, pk=pk)
    if request.method == 'POST':
        user = secretaire.user
        user.delete()  # Cela supprimera aussi le secrétaire à cause de la relation OneToOne
        messages.success(request, 'Compte secrétaire supprimé avec succès!')
        return redirect('dashboard')
    return render(request, 'gestion_cabinet/secretaire_confirm_delete.html', {'secretaire': secretaire})

@login_required
@secretaire_required
def marquer_rdv_paye(request, rdv_id):
    rendez_vous = get_object_or_404(RendezVous, id=rdv_id)
    
    # Vérification supplémentaire que l'utilisateur est bien une secrétaire
    if not hasattr(request.user, 'secretaire_profile'):
        messages.error(request, "Seules les secrétaires peuvent modifier le statut de paiement.")
        return redirect('rendez_vous_list')
    
    if rendez_vous.statut_paiement != 'REGLE':
        rendez_vous.statut_paiement = 'REGLE'
        rendez_vous.save()
        messages.success(request, 'Le paiement a été enregistré avec succès.')
    return redirect('rendez_vous_list')

@login_required
@dentiste_required
def consultation_update(request, pk):
    consultation = get_object_or_404(Consultation, pk=pk)
    
    # Vérifier que c'est bien le dentiste qui a fait la consultation
    if request.user.dentiste_profile != consultation.rendez_vous.dentiste:
        messages.error(request, "Vous n'avez pas la permission de modifier cette consultation.")
        return redirect('consultation_detail', pk=pk)
    
    if request.method == 'POST':
        form = ConsultationForm(request.POST, instance=consultation)
        if form.is_valid():
            form.save()
            messages.success(request, 'Consultation modifiée avec succès!')
            return redirect('consultation_detail', pk=consultation.pk)
    else:
        form = ConsultationForm(instance=consultation)
    
    return render(request, 'gestion_cabinet/consultation_form.html', {
        'form': form,
        'consultation': consultation,
        'is_update': True
    })

@login_required
@secretaire_required
def definir_montant_rdv(request, rdv_id):
    # Vérification explicite du rôle de secrétaire
    if not hasattr(request.user, 'secretaire_profile'):
        messages.error(request, "Accès réservé aux secrétaires.")
        return redirect('rendez_vous_list')
        
    rendez_vous = get_object_or_404(RendezVous, id=rdv_id)
    
    if request.method == 'POST':
        form = RendezVousSecretaireForm(request.POST, instance=rendez_vous)
        if form.is_valid():
            form.save()
            messages.success(request, 'Montant défini avec succès !')
            return redirect('rendez_vous_list')
    else:
        form = RendezVousSecretaireForm(instance=rendez_vous)
    
    return render(request, 'gestion_cabinet/definir_montant_form.html', {
        'form': form,
        'rendez_vous': rendez_vous
    })

def logout_view(request):
    logout(request)
    messages.success(request, 'Vous avez été déconnecté avec succès.')
    return redirect('home')
