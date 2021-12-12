from core.schema import signal_mutation_module_validate
from django.db.models import OuterRef, Subquery, Avg, Q
from django.db.models.expressions import RawSQL
from core import filter_validity
import graphene
import graphene_django_optimizer as gql_optimizer
from core.schema import TinyInt, SmallInt, OpenIMISMutation, OrderedDjangoFilterConnectionField
from .models import ClaimMutation,SSFScheme
from django.core.exceptions import ValidationError, PermissionDenied
from django.utils.translation import gettext as _
from graphene_django.filter import DjangoFilterConnectionField

from .gql_queries import *
from .gql_mutations import *
from sosys.models import ClaimDocumentsMaster


class ssfSchemaType(DjangoObjectType):
    class Meta:
        model = SSFScheme

class Query(graphene.ObjectType):
    claims = OrderedDjangoFilterConnectionField(
        ClaimGQLType,
        diagnosisVariance=graphene.Int(),
        codeIsNot=graphene.String(),
        rejectList=graphene.String(),
        orderBy=graphene.List(of_type=graphene.String),
    )
    claim_attachments = DjangoFilterConnectionField(ClaimAttachmentGQLType)
    claim_admins = DjangoFilterConnectionField(ClaimAdminGQLType)
    ssf = DjangoFilterConnectionField(SsfSchemeServiceGQLType)
    claim_admins_str = DjangoFilterConnectionField(
        ClaimAdminGQLType,
        str=graphene.String(),
    )
    dashboard = graphene.Field(DashboardGQLType)
    # GetSpouse = DjangoFilterConnectionField(SpouseGQLType)
    contributor_employer = DjangoFilterConnectionField(EmployerInsureeGQLType)
    claim_officers = DjangoFilterConnectionField(ClaimOfficerGQLType)
    employers = DjangoFilterConnectionField(EmployerGQLType)
    banks = DjangoFilterConnectionField(BankGQLType)
    bankBranches = DjangoFilterConnectionField(BankBranchGQLType)
    ClaimRecommend = DjangoFilterConnectionField(ClaimRecommendGQLType)
    claim_documents_master = DjangoFilterConnectionField(ClaimDocumentsMasterGQLType)
    sub_products = DjangoFilterConnectionField(SubProductGQLType)


    def resolve_sub_products(self,info,**kwargs):
        if not info.context.user.has_perms(ClaimConfig.gql_query_claims_perms):
            raise PermissionDenied(_("unauthorized"))
        query = SubProduct.objects.filter(status="A")
        return gql_optimizer.query(query.all(), info)

    def resolve_dashboard(root, info):
        Accident_clamAPP = Claim.objects.filter(product__code='SSF0002',validity_to__isnull=True).count()
        Accident_recomm = Claim.objects.filter(product__code='SSF0002',status=6,validity_to__isnull=True).count()
        Accident_forwarded = Claim.objects.filter(product__code='SSF0002',status=9,validity_to__isnull=True).count()
        Accident_valuated = Claim.objects.filter(product__code='SSF0002',status=16,validity_to__isnull=True).count()
        Accident_reject = Claim.objects.filter(product__code='SSF0002',status=1,validity_to__isnull=True).count()
        Accident_enter = Claim.objects.filter(product__code='SSF0002',status=2,validity_to__isnull=True).count()
        Accident_checked = Claim.objects.filter(product__code='SSF0002',status=4,validity_to__isnull=True).count()
        
        Medical_clamAPP = Claim.objects.filter(product__code='SSF0001',validity_to__isnull=True).count()
        Medical_forwarded = Claim.objects.filter(product__code='SSF0001',status=9,validity_to__isnull=True).count()
        Medical_valuated = Claim.objects.filter(product__code='SSF0001',status=16,validity_to__isnull=True).count()
        Medical_reject = Claim.objects.filter(product__code='SSF0001',status=1,validity_to__isnull=True).count()
        Medical_enter = Claim.objects.filter(product__code='SSF0001',status=2,validity_to__isnull=True).count()
        Medical_checked = Claim.objects.filter(product__code='SSF0001',status=6,validity_to__isnull=True).count()

        # Data set 2
        work_place_accident = Claim.objects.filter(Q(subProduct__type='W') ,validity_to__isnull=True).count()
        accident = Claim.objects.filter(Q(subProduct__type='A'),validity_to__isnull=True).count()
        occupational_disease = Claim.objects.filter(Q(subProduct__type='D'),validity_to__isnull=True).count()
        other = Claim.objects.filter(Q(subProduct__type='O'),validity_to__isnull=True).count()

        # Data set 3
        range1 = Claim.objects.filter(approved__gte=1, approved__lte=100000, validity_to__isnull=True).count()  # 1-100000
        range2 = Claim.objects.filter(approved__gte=100001, approved__lte=200000,validity_to__isnull=True).count()  # 100001-200000                                
        range3 = Claim.objects.filter(approved__gte=200001, approved__lte=300000,validity_to__isnull=True).count()  # 200001-300000
        range4 = Claim.objects.filter(approved__gte=300001, approved__lte=400000,validity_to__isnull=True).count()  # 300001-400000
        range5 = Claim.objects.filter(approved__gte=400001,validity_to__isnull=True).count() # above 400000
        
        return DashboardGQLType(
            Accident_recommended_by_employer=Accident_recomm,
            Accident_in_progress = Accident_checked,
            Accident_settled = Accident_valuated,
            Accident_claim_application = Accident_clamAPP,
            Accident_rejected = Accident_reject,
            Accident_forwarded = Accident_forwarded,
            Accident_entered = Accident_enter,
            
           
            Medical_in_progress = Medical_checked,
            Medical_settled = Medical_valuated,
            Medical_claim_application = Medical_clamAPP,
            Medical_rejected = Medical_reject,
            Medical_forwarded = Medical_forwarded,
            Medical_entered = Medical_enter,

            work_place_accident = work_place_accident,
            range1 = range1,
            range2 = range2,
            range3 = range3,
            range4 = range4,
            range5 = range5,
            accident = accident,
            occupational_disease = occupational_disease,
            other = other
        )

    def resolve_claim_documents_master(self,info,**kwargs):
        if not info.context.user.has_perms(ClaimConfig.gql_query_claims_perms):
            raise PermissionDenied(_("unauthorized"))
        query = ClaimDocumentsMaster.objects.filter(Status=True)
        return gql_optimizer.query(query.all(),info)


    def resolve_claims(self, info, **kwargs):
        if not info.context.user.has_perms(ClaimConfig.gql_query_claims_perms):
            raise PermissionDenied(_("unauthorized"))
        query = Claim.objects
        code_is_not = kwargs.get('codeIsNot', None)
        status =kwargs.get('status', None)
        rejectList =kwargs.get('rejectList', None)
        if rejectList:
            full_reject = Claim.objects.filter(status=1)
            partial_reject = Claim.objects.filter(~Q(status=1))
            partial_reject_item = partial_reject.filter(items__status = 2,validity_to__isnull = True)
            partial_reject_service = partial_reject.filter(services__status = 2,validity_to__isnull = True)
            # partial_reject = partial_reject_item.union(partial_reject_service)
            # query = full_reject.union(partial_reject)
            query = ((full_reject)|(partial_reject_item)|(partial_reject_service)).distinct()
            # print(query.query)
            print(query.defer('json_ext','adjustment','explanation','injured_body_part','dead_reason','dead_certificate_attachment','dead_certificate_attachment','accident_description','discharge_summary','check_attachment','check_remarks').query)
            # query = query

            return query.defer('json_ext','adjustment','explanation','injured_body_part','dead_reason','dead_certificate_attachment','dead_certificate_attachment','accident_description','discharge_summary','check_attachment','check_remarks')

        if code_is_not:
            query = query.exclude(code=code_is_not)
        variance = kwargs.get('diagnosisVariance', None)
        if variance:
            from core import datetime, datetimedelta
            last_year = datetime.date.today()+datetimedelta(years=-1)
            diag_avg = Claim.objects \
                            .filter(*filter_validity(**kwargs)) \
                            .filter(date_claimed__gt=last_year) \
                            .values('icd__code') \
                            .filter(icd__code=OuterRef('icd__code')) \
                            .annotate(diag_avg=Avg('approved')).values('diag_avg')
            variance_filter = Q(claimed__gt=(1 + variance/100) * Subquery(diag_avg))
            if not ClaimConfig.gql_query_claim_diagnosis_variance_only_on_existing:
                diags = Claim.objects \
                    .filter(*filter_validity(**kwargs)) \
                    .filter(date_claimed__gt=last_year).values('icd__code').distinct()
                variance_filter = (variance_filter | ~Q(icd__code__in=diags))
            query = query.filter(variance_filter)
        return gql_optimizer.query(query.all(), info)

    def resolve_claim_attachments(self, info, **kwargs):
        if not info.context.user.has_perms(ClaimConfig.gql_query_claims_perms):
            raise PermissionDenied(_("unauthorized"))
        pass

    def resolve_claim_admins(self, info, **kwargs):
        if not info.context.user.has_perms(ClaimConfig.gql_query_claim_admins_perms):
            raise PermissionDenied(_("unauthorized"))
        pass
    
    def resolve_ssf(self, info, **kwargs):
        if not info.context.user.has_perms(ClaimConfig.gql_query_claim_admins_perms):
            raise PermissionDenied(_("unauthorized"))
        pass
    
    def resolve_claim_admins_str(self, info, **kwargs):
        if not info.context.user.has_perms(ClaimConfig.gql_query_claim_admins_perms):
            raise PermissionDenied(_("unauthorized"))
        filters = [*filter_validity(**kwargs)]
        str = kwargs.get('str')
        if str is not None:
            filters += [Q(code__icontains=str) | Q(last_name__icontains=str) | Q(other_names__icontains=str)]
        return ClaimAdmin.filter_queryset().filter(*filters)

    def resolve_claim_officers(self, info, **kwargs):
        if not info.context.user.has_perms(ClaimConfig.gql_query_claim_officers_perms):
            raise PermissionDenied(_("unauthorized"))
        pass


class Mutation(graphene.ObjectType):
    create_claim = CreateClaimMutation.Field()
    claim_code= CreateClaimCodeMutation.Field()
    update_claim = UpdateClaimMutation.Field()
    create_claim_attachment = CreateAttachmentMutation.Field()
    update_claim_attachment = UpdateAttachmentMutation.Field()
    delete_claim_attachment = DeleteAttachmentMutation.Field()
    submit_claims = SubmitClaimsMutation.Field()
    forward_claims = ForwardClaimsMutation.Field()
    select_claims_for_feedback = SelectClaimsForFeedbackMutation.Field()
    deliver_claim_feedback = DeliverClaimFeedbackMutation.Field()
    bypass_claims_feedback = BypassClaimsFeedbackMutation.Field()
    skip_claims_feedback = SkipClaimsFeedbackMutation.Field()
    select_claims_for_review = SelectClaimsForReviewMutation.Field()
    save_claim_review = SaveClaimReviewMutation.Field()
    deliver_claims_review = DeliverClaimsReviewMutation.Field()
    bypass_claims_review = BypassClaimsReviewMutation.Field()
    skip_claims_review = SkipClaimsReviewMutation.Field()
    process_claims = ProcessClaimsMutation.Field()
    delete_claims = DeleteClaimsMutation.Field()


def on_claim_mutation(sender, **kwargs):
    uuids = kwargs['data'].get('uuids', [])
    if not uuids:
        uuid = kwargs['data'].get('claim_uuid', None)
        uuids = [uuid] if uuid else []
    if not uuids:
        return []
    impacted_claims = Claim.objects.filter(uuid__in=uuids).all()
    for claim in impacted_claims:
        ClaimMutation.objects.create(
            claim=claim, mutation_id=kwargs['mutation_log_id'])
    return []


def bind_signals():
    signal_mutation_module_validate["claim"].connect(on_claim_mutation)
