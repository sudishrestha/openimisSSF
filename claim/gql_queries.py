import graphene
from core import prefix_filterset, ExtendedConnection, filter_validity, Q, assert_string_length
from graphene_django import DjangoObjectType
from insuree.schema import InsureeGQLType
from location.schema import HealthFacilityGQLType
from medical.schema import DiagnosisGQLType
from claim_batch.schema import BatchRunGQLType
from .models import Claim, ClaimAdmin, Feedback, ClaimItem, ClaimService, ClaimAttachment,SSFScheme
from core.models import Officer
from sosys.models import Dependent,Employer,InsureeEmployer,Bank,BankBranch, ClaimRecommend,ClaimDocumentsMaster,SubProduct
from insuree.schema import InsureeGQLType
from product.schema import ProductGQLType

class ClaimAdminGQLType(DjangoObjectType):
    """
    Details about a Claim Administrator
    """

    class Meta:
        model = ClaimAdmin
        exclude_fields = ('row_id',)
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "uuid": ["exact"],
            "code": ["exact", "icontains"],
            "last_name": ["exact", "icontains"],
            "other_names": ["exact", "icontains"],
            **prefix_filterset("health_facility__", HealthFacilityGQLType._meta.filter_fields),
        }
        connection_class = ExtendedConnection

    @classmethod
    def get_queryset(cls, queryset, info):
        queryset = queryset.filter(*filter_validity())
        return queryset


class SsfSchemeServiceGQLType(DjangoObjectType):
    """
    Details about a SSF Scheme
    """

    class Meta:
        model = SSFScheme
        exclude_fields = ('row_id',)
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "SCH_NAME": ["exact"]
        }
        connection_class = ExtendedConnection

    @classmethod
    def get_queryset(cls, queryset, info):
        queryset = queryset.filter()
        return queryset

class ClaimOfficerGQLType(DjangoObjectType):
    """
    Details about a Claim Officer
    """

    class Meta:
        model = Officer
        exclude_fields = ('row_id',)
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "uuid": ["exact"],
            "code": ["exact", "icontains"],
            "last_name": ["exact", "icontains"],
            "other_names": ["exact", "icontains"],
        }
        connection_class = ExtendedConnection

    @classmethod
    def get_queryset(cls, queryset, info):
        queryset = queryset.filter(*filter_validity())
        return queryset


class EmployerGQLType(DjangoObjectType):
    """""
        Contains the Employers of contributor 
    """""
    class Meta:
        model = Employer
        interfaces = (graphene.relay.Node,)
        exclude_fields = ('row_id',)
        filter_fields = {
            "E_SSID": ["exact"],
            "EmployerNameNep":["exact", "icontains"]
        }
        connection_class = ExtendedConnection

def get_user_by_userId(userId=None):
    if(userId):
        code = None
        from django.db import connection
        sql = """\
                SET NOCOUNT ON;
                EXEC  [dbo].[uspGetUserWithRole] @userId = '""" + str(userId) + """';
            """
        with connection.cursor() as cur:
            try:
                cur.execute(sql)
                result_set = cur.fetchone()
                return result_set
            except e:
                print(e)
            finally:
                cur.close()
                
class ClaimGQLType(DjangoObjectType):
    """
    Main element for a Claim. It can contain items and/or services.
    The filters are possible on BatchRun, Insuree, HealthFacility, Admin and ICD in addition to the Claim fields
    themselves.
    """
    attachments_count = graphene.Int()
    client_mutation_id = graphene.String()
    entry_by_login_id = graphene.String()
    submit_by_login_id = graphene.String()
    process_by_login_id = graphene.String()
    review_by_login_id = graphene.String()
    class Meta:
        model = Claim
        exclude_fields = ('row_id',)
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "uuid": ["exact"],
            "scheme_type": ["exact"],
            "code": ["exact", "istartswith", "icontains", "iexact"],
            "status": ["exact"],
            "date_claimed": ["exact", "lt", "lte", "gt", "gte"],
            "date_from": ["exact", "lt", "lte", "gt", "gte"],
            "date_to": ["exact", "lt", "lte", "gt", "gte"],
            "feedback_status": ["exact"],
            "review_status": ["exact"],
            "claimed": ["exact", "lt", "lte", "gt", "gte"],
            "approved": ["exact", "lt", "lte", "gt", "gte"],
            "visit_type": ["exact"],
            "attachments_count__value": ["exact", "lt", "lte", "gt", "gte"],
            **prefix_filterset("icd__", DiagnosisGQLType._meta.filter_fields),
            **prefix_filterset("admin__", ClaimAdminGQLType._meta.filter_fields),
            **prefix_filterset("health_facility__", HealthFacilityGQLType._meta.filter_fields),
            **prefix_filterset("insuree__", InsureeGQLType._meta.filter_fields),
            **prefix_filterset("batch_run__", BatchRunGQLType._meta.filter_fields),
            **prefix_filterset("employer__", EmployerGQLType._meta.filter_fields),
            **prefix_filterset("product__", ProductGQLType._meta.filter_fields),
        }
        connection_class = ExtendedConnection

    def resolve_attachments_count(self, info):
        return self.attachments.filter(validity_to__isnull=True).count()

    def resolve_items(self, info):
        return self.items.filter(validity_to__isnull=True)

    def resolve_services(self, info):
        return self.services.filter(validity_to__isnull=True)
        
    def resolve_entry_by_login_id(self, info):
        entryBy = get_user_by_userId(self.audit_user_id)
        if entryBy:
            return entryBy[2]
        else:
            return None
    def resolve_submit_by_login_id(self, info):
        entryBy = get_user_by_userId(self.audit_user_id_submit)
        if entryBy:
            return entryBy[2]
        else:
            return None
    def resolve_process_by_login_id(self, info):
        entryBy = get_user_by_userId(self.audit_user_id_process)
        if entryBy:
            return entryBy[2]
        else:
            return None
    def resolve_review_by_login_id(self, info):
        if self.audit_user_id_review:
            entryBy = get_user_by_userId(self.audit_user_id_review)
            if entryBy:
                return entryBy[2]
        return None
    def resolve_client_mutation_id(self, info):
        claim_mutation = self.mutations.select_related(
            'mutation').filter(mutation__status=0).first()
        return claim_mutation.mutation.client_mutation_id if claim_mutation else None

    @classmethod
    def get_queryset(cls, queryset, info):
        return Claim.get_queryset(queryset, info)

class ClaimDocumentsMasterGQLType(DjangoObjectType):
    class Meta:
        model = ClaimDocumentsMaster
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "id":["exact"],
            "DocName":["exact","icontains"],
            "UseBy":["icontains"]
        }

    connection_class = ExtendedConnection

class ClaimAttachmentGQLType(DjangoObjectType):
    doc = graphene.String()

    class Meta:
        model = ClaimAttachment
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "id": ["exact"],
            "type": ["exact", "icontains"],
            "title": ["exact", "icontains"],
            "date": ["exact", "lt", "lte", "gt", "gte"],
            "filename": ["exact", "icontains"],
            "mime": ["exact", "icontains"],
            "url": ["exact", "icontains"],
            "documentFrom":["exact"],
            **prefix_filterset("claim__", ClaimGQLType._meta.filter_fields),
            **prefix_filterset("masterDocument__", ClaimDocumentsMasterGQLType._meta.filter_fields),
        }
        connection_class = ExtendedConnection

    @classmethod
    def get_queryset(cls, queryset, info):
        queryset = queryset.filter(*filter_validity())
        return queryset


class FeedbackGQLType(DjangoObjectType):
    class Meta:
        model = Feedback
        exclude_fields = ('row_id',)


class ClaimItemGQLType(DjangoObjectType):
    """
    Contains the items within a specific Claim
    """

    class Meta:
        model = ClaimItem
        exclude_fields = ('row_id',)


class ClaimServiceGQLType(DjangoObjectType):
    """
    Contains the services within a specific Claim
    """

    class Meta:
        model = ClaimService
        exclude_fields = ('row_id',)


class ClaimRecommendGQLType(DjangoObjectType):
    class Meta:
        model=ClaimRecommend
        interfaces=(graphene.relay.Node,)
        filter_fields={
            "id":["exact"],
            "claim":["exact"],
            **prefix_filterset("claim__", ClaimGQLType._meta.filter_fields),
        }

# class SpouseGQLType(DjangoObjectType):
#     class Meta:
#         model = Insuree
#         interfaces = (graphene.relay.Node,)
#         exclude_fields = ('row_id',)
#         filter_fields = {
#             "DependentId":["exact"],
#             "p_ssid":["exact"],
#         }
#         connection_class = ExtendedConnection

class EmployerInsureeGQLType(DjangoObjectType):
    class Meta:
        model = InsureeEmployer
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "id":["exact"],
            "employer":["exact"],
            "insuree":["exact"],
            **prefix_filterset("employer__", EmployerGQLType._meta.filter_fields),
            **prefix_filterset("insuree__", InsureeGQLType._meta.filter_fields)

        }
        connection_class = ExtendedConnection

class DashboardGQLType(graphene.ObjectType):
    # contains summary for dashboard graphs
    # Data set 1
    Accident_recommended_by_employer = graphene.Int()
    Accident_in_progress = graphene.Int()
    Accident_settled = graphene.Int()
    Accident_claim_application = graphene.Int()
    Accident_rejected = graphene.Int()
    Accident_forwarded = graphene.Int()
    Accident_entered = graphene.Int()
    
   
    Medical_in_progress = graphene.Int()
    Medical_settled = graphene.Int()
    Medical_claim_application = graphene.Int()
    Medical_rejected = graphene.Int()
    Medical_forwarded = graphene.Int()
    Medical_entered = graphene.Int()

    # Data set 2
    work_place_accident = graphene.Int()
    accident = graphene.Int()
    occupational_disease = graphene.Int()
    other = graphene.Int()

    #Data set 3
    range1 = graphene.Int() #1-100000
    range2 = graphene.Int() #100001-200000
    range3 = graphene.Int() #200001-300000
    range4 = graphene.Int() #300001-400000
    range5 = graphene.Int() #above 400000

class BankGQLType(DjangoObjectType):
    class Meta:
        model = Bank
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "BankId":["exact"],
            "BankNameEng":["exact", "icontains"],
        }
        connection_class = ExtendedConnection

class BankBranchGQLType(DjangoObjectType):
    class Meta:
        model = BankBranch
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "BranchId":["exact"],
            "Bank":["exact"],
            **prefix_filterset("Bank__", BankGQLType._meta.filter_fields),
        }
        connection_class = ExtendedConnection

class SubProductGQLType(DjangoObjectType):
    class Meta:
        model = SubProduct
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "id":["exact"],
            "sch_name":["exact","icontains"],
            "sch_name_eng":["exact","icontains"],
            "type":["exact"],
            **prefix_filterset("product__", ProductGQLType._meta.filter_fields),
        }
        connection_class = ExtendedConnection