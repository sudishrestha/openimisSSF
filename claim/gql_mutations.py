from inspect import Parameter
import logging
import uuid
import pathlib
import base64
import graphene
from .apps import ClaimConfig
from claim.validations import validate_claim, get_claim_category, validate_assign_prod_to_claimitems_and_services, \
    process_dedrem, approved_amount
from core import prefix_filterset, ExtendedConnection, filter_validity, assert_string_length
from core.schema import TinyInt, SmallInt, OpenIMISMutation, OrderedDjangoFilterConnectionField
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import ValidationError, PermissionDenied
from django.db.models import Sum, CharField
from django.db.models.functions import Coalesce
from django.utils.translation import gettext as _
from graphene import InputObjectType
from location.schema import UserDistrict
from .models import Claim, Feedback, ClaimDetail, ClaimItem, ClaimService, ClaimAttachment, ClaimDedRem
from product.models import ProductItemOrService
import requests
import json
from location.models import HealthFacility
from datetime import datetime,date

logger = logging.getLogger(__name__)

class ClaimItemInputType(InputObjectType):
    id = graphene.Int(required=False)
    item_id = graphene.Int(required=True)
    status = TinyInt(required=True)
    qty_provided = graphene.Decimal(
        max_digits=18, decimal_places=2, required=False)
    qty_approved = graphene.Decimal(
        max_digits=18, decimal_places=2, required=False)
    price_asked = graphene.Decimal(
        max_digits=18, decimal_places=2, required=False)
    price_adjusted = graphene.Decimal(
        max_digits=18, decimal_places=2, required=False)
    price_approved = graphene.Decimal(
        max_digits=18, decimal_places=2, required=False)
    price_valuated = graphene.Decimal(
        max_digits=18, decimal_places=2, required=False)
    explanation = graphene.String(required=False)
    justification = graphene.String(required=False)
    rejection_reason = SmallInt(required=False)

    validity_from_review = graphene.DateTime(required=False)
    validity_to_review = graphene.DateTime(required=False)
    limitation_value = graphene.Decimal(
        max_digits=18, decimal_places=2, required=False)
    limitation = graphene.String(required=False)
    # policy_id
    remunerated_amount = graphene.Decimal(
        max_digits=18, decimal_places=2, required=False)
    deductable_amount = graphene.Decimal(
        max_digits=18, decimal_places=2, required=False)
    exceed_ceiling_amount = graphene.Decimal(
        max_digits=18, decimal_places=2, required=False)
    price_origin = graphene.String(required=False)
    exceed_ceiling_amount_category = graphene.Decimal(
        max_digits=18, decimal_places=2, required=False)


class ClaimServiceInputType(InputObjectType):
    id = graphene.Int(required=False)
    legacy_id = graphene.Int(required=False)
    service_id = graphene.Int(required=True)
    status = TinyInt(required=True)
    qty_provided = graphene.Decimal(
        max_digits=18, decimal_places=2, required=False)
    qty_approved = graphene.Decimal(
        max_digits=18, decimal_places=2, required=False)
    price_asked = graphene.Decimal(
        max_digits=18, decimal_places=2, required=False)
    price_adjusted = graphene.Decimal(
        max_digits=18, decimal_places=2, required=False)
    price_approved = graphene.Decimal(
        max_digits=18, decimal_places=2, required=False)
    price_valuated = graphene.Decimal(
        max_digits=18, decimal_places=2, required=False)
    explanation = graphene.String(required=False)
    justification = graphene.String(required=False)
    rejection_reason = SmallInt(required=False)
    validity_to = graphene.DateTime(required=False)
    validity_from_review = graphene.DateTime(required=False)
    validity_to_review = graphene.DateTime(required=False)
    audit_user_id_review = graphene.Int(required=False)
    limitation_value = graphene.Decimal(
        max_digits=18, decimal_places=2, required=False)
    limitation = graphene.String(max_length=1, required=False)
    policy_id = graphene.Int(required=False)
    remunerated_amount = graphene.Decimal(
        max_digits=18, decimal_places=2, required=False)
    deductable_amount = graphene.Decimal(
        max_digits=18, decimal_places=2, required=False,
        description="deductable is spelled with a, not deductible")
    exceed_ceiling_amount = graphene.Decimal(
        max_digits=18, decimal_places=2, required=False)
    price_origin = graphene.String(max_length=1, required=False)
    exceed_ceiling_amount_category = graphene.Decimal(
        max_digits=18, decimal_places=2, required=False)


class FeedbackInputType(InputObjectType):
    id = graphene.Int(required=False, read_only=True)
    care_rendered = graphene.Boolean(required=False)
    payment_asked = graphene.Boolean(required=False)
    drug_prescribed = graphene.Boolean(required=False)
    drug_received = graphene.Boolean(required=False)
    asessment = SmallInt(
        required=False,
        description="Be careful, this field name has a typo")
    officer_id = graphene.Int(required=False)
    feedback_date = graphene.DateTime(required=False)
    validity_from = graphene.DateTime(required=False)
    validity_to = graphene.DateTime(required=False)


class ClaimCodeInputType(graphene.String):

    @staticmethod
    def coerce_string(value):
        assert_string_length(value, 60)
        return value

    serialize = coerce_string
    parse_value = coerce_string

    @staticmethod
    def parse_literal(ast):
        result = graphene.String.parse_literal(ast)
        assert_string_length(result, 60)
        return result


class ClaimGuaranteeIdInputType(graphene.String):

    @staticmethod
    def coerce_string(value):
        assert_string_length(value, 50)
        return value

    serialize = coerce_string
    parse_value = coerce_string

    @staticmethod
    def parse_literal(ast):
        result = graphene.String.parse_literal(ast)
        assert_string_length(result, 50)
        return result


class BaseAttachment:
    id = graphene.String(required=False, read_only=True)
    type = graphene.String(required=False)
    title = graphene.String(required=False)
    date = graphene.Date(required=False)
    filename = graphene.String(required=False)
    mime = graphene.String(required=False)
    url = graphene.String(required=False)
    masterDocument_id = graphene.Int(required = False)
    documentFrom = graphene.String(required = False)


class BaseAttachmentInputType(BaseAttachment, OpenIMISMutation.Input):
    """
    Claim attachment (without the document), used on its own
    """
    claim_uuid = graphene.String(required=True)


class Attachment(BaseAttachment):
    document = graphene.String(required=False)


class ClaimAttachmentInputType(Attachment, InputObjectType):
    """
    Claim attachment, used nested in claim object
    """
    pass


class AttachmentInputType(Attachment, OpenIMISMutation.Input):
    """
    Claim attachment, used on its own
    """
    claim_uuid = graphene.String(required=True)

class ClaimCodeGeneratorInputType(OpenIMISMutation.Input):
    coded_value = graphene.String(required=True)

class ClaimInputType(OpenIMISMutation.Input):
    id = graphene.Int(required=False, read_only=True)
    uuid = graphene.String(required=False)
    code = ClaimCodeInputType(required=True)
    insuree_id = graphene.Int(required=True)
    date_from = graphene.Date(required=True)
    date_to = graphene.Date(required=False)
    icd_id = graphene.Int(required=True)
    icd_1_id = graphene.Int(required=False)
    icd_2_id = graphene.Int(required=False)
    icd_3_id = graphene.Int(required=False)
    icd_4_id = graphene.Int(required=False)
    review_status = TinyInt(required=False)
    date_claimed = graphene.Date(required=True)
    date_processed = graphene.Date(required=False) 
    health_facility_id = graphene.Int(required=True)
    batch_run_id = graphene.Int(required=False)
    scheme_type = graphene.Int(required=False)
    category = graphene.String(max_length=1, required=False)
    visit_type = graphene.String(max_length=1, required=False)
    admin_id = graphene.Int(required=False)
    guarantee_id = ClaimGuaranteeIdInputType(required=False)
    explanation = graphene.String(required=False)
    adjustment = graphene.String(required=False)
    json_ext = graphene.types.json.JSONString(required=False)

    feedback_available = graphene.Boolean(default=False)
    feedback_status = TinyInt(required=False)
    feedback = graphene.Field(FeedbackInputType, required=False)
    items = graphene.List(ClaimItemInputType, required=False)
    services = graphene.List(ClaimServiceInputType, required=False)
    employer_id = graphene.String(required = False)
    discharge_summary = graphene.String(required = False)
    discharge_type = graphene.String(required = False)
    follow_up_date = graphene.Date(required=False)
    rest_period = graphene.Int(required=False)
    refer_to_date = graphene.Date(required = False)
    refer_to_health_facility_id = graphene.Int(required = False)
    # refer_by_claim_id = graphene.Int(required = False)
    refer_flag = graphene.Boolean(default= False)
    
    refer_from_date = graphene.Date(required=False)
    refer_from_health_facility_id = graphene.Int(required=False)
    hf_bank_id = graphene.Int(required= False)
    hf_branch_id = graphene.Int(required = False)
    hf_account_name = graphene.String(required = False)
    hf_account_number = graphene.String(required = False)

    is_admitted= graphene.String(required=False)
    condition_of_wound= graphene.String(required=False)
    reason_of_sickness= graphene.String(required=False)
    injured_body_part= graphene.String(required=False)
    is_dead= graphene.String(required=False)
    dead_date= graphene.Date(required=False)
    dead_time= graphene.String(required=False)
    dead_reason= graphene.String(required=False)
    dead_certificate_attachment = graphene.String(required = False)
    cancer= graphene.String(required=False)
    hiv = graphene.String(required=False)
    is_disable = graphene.String(required=False)
    high_bp= graphene.String(required=False)
    diabetes= graphene.String(required=False)
    heart_attack= graphene.String(required=False)    
    capability= graphene.String(required=False)
    accident_description= graphene.String(required=False)
    check_remarks = graphene.String(required=False)
    check_attachment = graphene.String(required=False)
    scheme_app_id = graphene.String(required=False)
    subProduct_id = graphene.Int(required=False)
    refer_from_hf_other = graphene.String(required=False)
    refer_to_hf_other = graphene.String(required=False)
    product_id = graphene.Int(required=False)
    is_reclaim = graphene.String(required=False)
    head_claim_id = graphene.Int(required=False)
    claim_for = graphene.Int(required=False)
    pay_to = graphene.Int(required=False)


class CreateClaimInputType(ClaimInputType):
    attachments = graphene.List(ClaimAttachmentInputType, required=False)


def reset_claim_before_update(claim):
    claim.date_to = None
    claim.icd_1 = None
    claim.icd_2 = None
    claim.icd_3 = None
    claim.icd_4 = None
    claim.guarantee_id = None
    claim.explanation = None
    claim.adjustment = None


def process_child_relation(user, data_children, claim_id, children, create_hook):
    claimed = 0
    from core.utils import TimeUtils
    for data_elt in data_children:
        claimed += data_elt['qty_provided'] * data_elt['price_asked']
        elt_id = data_elt.pop('id') if 'id' in data_elt else None
        if elt_id:
            # elt has been historized along with claim historization
            elt = children.get(id=elt_id)
            [setattr(elt, k, v) for k, v in data_elt.items()]
            elt.validity_from = TimeUtils.now()
            elt.audit_user_id = user.id_for_audit
            elt.claim_id = claim_id
            elt.save()
        else:
            data_elt['validity_from'] = TimeUtils.now()
            data_elt['audit_user_id'] = user.id_for_audit
            create_hook(claim_id, data_elt)

    return claimed


def item_create_hook(claim_id, item):
    # TODO: investigate 'availability' is mandatory,
    # but not in UI > always true?
    item['availability'] = True
    ClaimItem.objects.create(claim_id=claim_id, **item)


def service_create_hook(claim_id, service):
    ClaimService.objects.create(claim_id=claim_id, **service)


def create_file(date, claim_id, document):
    date_iso = date.isoformat()
    root = ClaimConfig.claim_attachments_root_path
    file_dir = '%s/%s/%s/%s' % (
        date_iso[0:4],
        date_iso[5:7],
        date_iso[8:10],
        claim_id
    )
    file_path = '%s/%s' % (file_dir, uuid.uuid4())
    pathlib.Path('%s/%s' % (root, file_dir)).mkdir(parents=True, exist_ok=True)
    f = open('%s/%s' % (root, file_path), "xb")
    f.write(base64.b64decode(document))
    f.close()
    return file_path


def create_attachment(claim_id, data):
    data["claim_id"] = claim_id
    from core import datetime
    now = datetime.datetime.now()
    if ClaimConfig.claim_attachments_root_path:
        # don't use data date as it may be updated by user afterwards!
        data['url'] = create_file(now, claim_id, data.pop('document'))
    data['validity_from'] = now
    data['documentFrom'] = 'A'
    ClaimAttachment.objects.create(**data)


def create_attachments(claim_id, attachments):
    for attachment in attachments:
        create_attachment(claim_id, attachment)

# def ad_to_bs_sosys_format(for_str=None,str=None):
#     print(for_str)
#     if(str):
#         parse_date = datetime.strptime(str,"%Y-%m-%d")
#         converted_date = (NepaliDate.to_nepali_date(date(parse_date.year, parse_date.month, parse_date.day))).strfdate('%Y.%m.%d')
#         if converted_date:
#             return converted_date
#         else:
#             return datetime.now().strftime('%Y.%m.%d')

def call_SP(parameter,schemeId,claimType="C"):
    code_initial = "I" + str(parameter)
    claim_code = ""
    import datetime
    currentYear = datetime.datetime.now()
    if claimType == "R":
        claim_code = generate_code("Null",parameter,schemeId,claimType)
    else:
        claim_code = generate_code(code_initial+str(currentYear.year)[1:],"Null",schemeId,claimType)

    return claim_code
    # else:
    #     return  "error"


def generate_code(claimCodeInitials,oldClaimCode,schemeId,claimType):
    code = None
    from django.db import connection
    sql = """\
            SET NOCOUNT ON;
            EXEC  [dbo].[uspClaimSequenceNo] @claimcodeinitials = '""" + claimCodeInitials + """',@oldclaimCode="""+oldClaimCode+""" ;      
            
        """
    # print(sql)
    with connection.cursor() as cur:
        try:
            cur.execute(sql)
            result_set = cur.fetchone()[0]
            print(result_set)
            code = result_set
            if claimType == 'C':
                #11 CHAR		 3 char  7 char	   2 char	    1 char
                #I<hospitalCode> <year>   <seqNo>  <schemeNo> <claimType>
                code = claimCodeInitials + str("{:07d}".format(result_set)) +str(schemeId)+ claimType
        except e:
            print(e)
        finally:
            cur.close()
    return code

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


def update_or_create_claim(data, user):
    items = data.pop('items') if 'items' in data else []
    services = data.pop('services') if 'services' in data else []
    if "client_mutation_id" in data:
        data.pop('client_mutation_id')
    if "client_mutation_label" in data:
        data.pop('client_mutation_label')
    claim_uuid = data.pop('uuid') if 'uuid' in data else None
    # update_or_create(uuid=claim_uuid, ...)
    # doesn't work because of explicit attempt to set null to uuid!
    prev_claim_id = None
    if claim_uuid:
        claim = Claim.objects.get(uuid=claim_uuid)
        prev_claim_id = claim.save_history()
        # reset the non required fields
        # (each update is 'complete', necessary to be able to set 'null')
        reset_claim_before_update(claim)
        [setattr(claim, key, data[key]) for key in data]
    else:
        claim = Claim.objects.create(**data)
    claimed = 0
    claimed += process_child_relation(user, items,
                                      claim.id, claim.items,
                                      item_create_hook)
    claimed += process_child_relation(user, services,
                                      claim.id, claim.services,
                                      service_create_hook)
    claim.claimed = claimed
    claim.save()
    return claim

class CreateClaimCodeMutation(OpenIMISMutation):
    """
    Create a new claim. The claim items and services can all be entered with this call
    """
    _mutation_module = "claim"
    _mutation_class = "CreateClaimCodeMutation"
    generated_coded_value = graphene.String(required=True)
    hospital_code = graphene.String(required=True)

    class Input(ClaimCodeGeneratorInputType):
        pass
    
    @classmethod
    def mutate(cls, root, info, input):
        def on_resolve(payload):
            try:
                payload.client_mutation_id = input.get("client_mutation_id")
                payload.hospital_code = input.get("coded_value")
                payload.generated_coded_value =cls.callSP(cls,input.get("coded_value")) 

            except Exception as ex:
                raise Exception(
                    (str(ex)+"Cannot set client_mutation_id in the payload object {}").format(
                        repr(payload) 
                    )
                )
            return payload
        from graphene.utils.thenables import maybe_thenable
        result = cls.mutate_and_get_payload(root, info, **input)
        return maybe_thenable(result, on_resolve)
    
    def callSP(cls,hosCode):
        code_value= "I"+str(hosCode)
        claim_code=cls.generateCode(code_value)
        return claim_code
        # else:
        #     return  "error"
        
    def generateCode(claimCodeInitials):
        code= None
        from django.db import connection
        sql = """\
                DECLARE @return_value int;
                EXEC @return_value = [dbo].[uspClaimSequenceNo] @claimcodeinitials = '""" +claimCodeInitials +"""' ;      
                SELECT	'Return Value' = @return_value;
            """
        # print(sql)
        with connection.cursor() as cur:
            try:
                cur.execute(sql)
                result_set = cur.fetchone()[0]
                import datetime
                currentYear = datetime.datetime.now()
                code = claimCodeInitials +str(currentYear.year)[1:]+ str("{:07d}".format(result_set))+"01C"
            finally:
                cur.close()
        return code
class CreateClaimMutation(OpenIMISMutation):
    """
    Create a new claim. The claim items and services can all be entered with this call
    """
    _mutation_module = "claim"
    _mutation_class = "CreateClaimMutation"

    class Input(CreateClaimInputType):
        pass

    @classmethod
    def async_mutate(cls, user, **data):
        try:
            # TODO move this verification to OIMutation
            if type(user) is AnonymousUser or not user.id:
                raise ValidationError(
                    _("mutation.authentication_required"))
            if not user.has_perms(ClaimConfig.gql_mutation_create_claims_perms):
                raise PermissionDenied(_("unauthorized"))
            health_facility = HealthFacility.objects.filter(
                id=data['health_facility_id'],
                validity_to__isnull=True,
            ).first()
            claim_type = 'R' if 'is_reclaim' in data and data['is_reclaim'] == 'true' else 'C'
            parameter = health_facility.code
            if claim_type == 'R':
                old_claim = Claim.objects.filter(id=data['head_claim_id'],validity_to__isnull=True).first()
                parameter = old_claim.code
            data['code']=call_SP(parameter,"01" if data['product_id']=="2" else "02",claim_type)
            # Claim code unicity should be enforced at DB Scheme level...
            if Claim.objects.filter(code=data['code']).exists():
                return [{
                    'message': _("claim.mutation.duplicated_claim_code") % {'code': data['code']},
                }]
            data['audit_user_id'] = user.id_for_audit
            data['status'] = Claim.STATUS_ENTERED
            # print('qwerty',data)
            from core.utils import TimeUtils
            data['validity_from'] = TimeUtils.now()
            attachments = data.pop('attachments') if 'attachments' in data else None
            claim = update_or_create_claim(data, user)
            if attachments:
                create_attachments(claim.id, attachments)
            return None
        except Exception as exc:
            return [{
                'message': _("claim.mutation.failed_to_create_claim") % {'code': data['code']},
                'detail': str(exc)}]


class UpdateClaimMutation(OpenIMISMutation):
    """
    Update a claim. The claim items and services can all be updated with this call
    """
    _mutation_module = "claim"
    _mutation_class = "UpdateClaimMutation"

    class Input(ClaimInputType):
        pass

    @classmethod
    def async_mutate(cls, user, **data):
        try:
            # TODO move this verification to OIMutation
            if type(user) is AnonymousUser or not user.id:
                raise ValidationError(
                    _("mutation.authentication_required"))
            if not user.has_perms(ClaimConfig.gql_mutation_update_claims_perms):
                raise PermissionDenied(_("unauthorized"))
            data['audit_user_id'] = user.id_for_audit
            update_or_create_claim(data, user)
            return None
        except Exception as exc:
            return [{
                'message': _("claim.mutation.failed_to_update_claim") % {'code': data['code']},
                'detail': str(exc)}]


class CreateAttachmentMutation(OpenIMISMutation):
    _mutation_module = "claim"
    _mutation_class = "AddClaimAttachmentMutation"

    class Input(AttachmentInputType):
        pass

    @classmethod
    def async_mutate(cls, user, **data):
        try:
            if user.is_anonymous or not user.has_perms(ClaimConfig.gql_mutation_update_claims_perms):
                raise PermissionDenied(_("unauthorized"))
            if "client_mutation_id" in data:
                data.pop('client_mutation_id')
            if "client_mutation_label" in data:
                data.pop('client_mutation_label')
            claim_uuid = data.pop("claim_uuid")
            queryset = Claim.objects.filter(*filter_validity())
            if settings.ROW_SECURITY:
                dist = UserDistrict.get_user_districts(user._u)
                queryset = queryset.filter(
                    health_facility__location__id__in=[
                        l.location_id for l in dist]
                )
            claim = queryset.filter(uuid=claim_uuid).first()
            if not claim:
                raise PermissionDenied(_("unauthorized"))
            create_attachment(claim.id, data)
            return None
        except Exception as exc:
            return [{
                'message': _("claim.mutation.failed_to_attach_document") % {'code': claim.code},
                'detail': str(exc)}]


class UpdateAttachmentMutation(OpenIMISMutation):
    _mutation_module = "claim"
    _mutation_class = "UpdateAttachmentMutation"

    class Input(BaseAttachmentInputType):
        pass

    @classmethod
    def async_mutate(cls, user, **data):
        try:
            if not user.has_perms(ClaimConfig.gql_mutation_update_claims_perms):
                raise PermissionDenied(_("unauthorized"))
            queryset = ClaimAttachment.objects.filter(*filter_validity())
            if settings.ROW_SECURITY:
                from location.models import UserDistrict
                dist = UserDistrict.get_user_districts(user._u)
                queryset = queryset.select_related("claim") \
                    .filter(
                    claim__health_facility__location__id__in=[
                        l.location_id for l in dist]
                )
            attachment = queryset \
                .filter(id=data['id']) \
                .first()
            if not attachment:
                raise PermissionDenied(_("unauthorized"))
            attachment.save_history()
            data['audit_user_id'] = user.id_for_audit
            [setattr(attachment, key, data[key]) for key in data]
            attachment.save()
            return None
        except Exception as exc:
            return [{
                'message': _("claim.mutation.failed_to_update_claim_attachment") % {
                    'code': attachment.claim.code,
                    'filename': attachment.filename
                },
                'detail': str(exc)}]


class DeleteAttachmentMutation(OpenIMISMutation):
    _mutation_module = "claim"
    _mutation_class = "DeleteClaimAttachmentMutation"

    class Input(OpenIMISMutation.Input):
        id = graphene.String()

    @classmethod
    def async_mutate(cls, user, **data):
        try:
            if not user.has_perms(ClaimConfig.gql_mutation_update_claims_perms):
                raise PermissionDenied(_("unauthorized"))
            queryset = ClaimAttachment.objects.filter(*filter_validity())
            if settings.ROW_SECURITY:
                from location.models import UserDistrict
                dist = UserDistrict.get_user_districts(user._u)
                queryset = queryset.select_related("claim") \
                    .filter(
                    claim__health_facility__location__id__in=[
                        l.location_id for l in dist]
                )
            attachment = queryset \
                .filter(id=data['id']) \
                .first()
            if not attachment:
                raise PermissionDenied(_("unauthorized"))
            attachment.delete_history()
            return None
        except Exception as exc:
            return [{
                'message': _("claim.mutation.failed_to_delete_claim_attachment") % {
                    'code': attachment.claim.code,
                    'filename': attachment.filename
                },
                'detail': str(exc)}]


class SubmitClaimsMutation(OpenIMISMutation):
    """
    Submit one or several claims.
    """
    _mutation_module = "claim"
    _mutation_class = "SubmitClaimsMutation"

    class Input(OpenIMISMutation.Input):
        uuids = graphene.List(graphene.String)

    @classmethod
    def async_mutate(cls, user, **data):
        if not user.has_perms(ClaimConfig.gql_mutation_submit_claims_perms):
            raise PermissionDenied(_("unauthorized"))
        errors = []
        for claim_uuid in data["uuids"]:
            c_errors = []
            claim = Claim.objects \
                .filter(uuid=claim_uuid,
                        validity_to__isnull=True) \
                .prefetch_related("items") \
                .prefetch_related("services") \
                .first()
            if claim is None:
                errors += {
                    'title': claim_uuid,
                    'list': [
                        {'message': _(
                            "claim.validation.id_does_not_exist") % {'id': claim_uuid}}
                    ]
                }
                continue
            claim.save_history()
            logger.debug("SubmitClaimsMutation: validating claim %s", claim_uuid)
            c_errors += validate_claim(claim, True)
            logger.debug("SubmitClaimsMutation: claim %s validated, nb of errors: %s", claim_uuid, len(c_errors))
            if len(c_errors) == 0:
                # if False:
                c_errors = validate_assign_prod_to_claimitems_and_services(claim)
                logger.debug("SubmitClaimsMutation: claim %s assigned, nb of errors: %s", claim_uuid, len(c_errors))
                c_errors += process_dedrem(claim, user.id_for_audit, False)
                logger.debug("SubmitClaimsMutation: claim %s processed for dedrem, nb of errors: %s", claim_uuid,
                             len(errors))
            c_errors += set_claim_submitted(claim, c_errors, user)
            logger.debug("SubmitClaimsMutation: claim %s set submitted", claim_uuid)
            if c_errors:
                errors.append({
                    'title': claim.code,
                    'list': c_errors
                })
        if len(errors) == 1:
            errors = errors[0]['list']
        logger.debug("SubmitClaimsMutation: claim done, errors: %s", len(errors))
        return errors

class ForwardClaimsMutation(OpenIMISMutation):
    """
    Submit one or several claims.
    """
    _mutation_module = "claim"
    _mutation_class = "ForwardClaimsMutation"

    class Input(OpenIMISMutation.Input):
        uuids = graphene.List(graphene.String)

    @classmethod
    def async_mutate(cls, user, **data):
        if not user.has_perms(ClaimConfig.gql_mutation_forward_claims_perms):
            raise PermissionDenied(_("unauthorized"))
        errors = []
        for claim_uuid in data["uuids"]:
            c_errors = []
            claim = Claim.objects \
                .filter(uuid=claim_uuid,
                        validity_to__isnull=True) \
                .prefetch_related("items") \
                .prefetch_related("services") \
                .first()
            if claim is None:
                errors += {
                    'title': claim_uuid,
                    'list': [
                        {'message': _(
                            "claim.validation.id_does_not_exist") % {'id': claim_uuid}}
                    ]
                }
                continue
            claim.save_history()
            logger.debug("ForwardClaimsMutation: validating claim %s", claim_uuid)
            c_errors += validate_claim(claim, True)
            logger.debug("ForwardClaimsMutation: claim %s validated, nb of errors: %s", claim_uuid, len(c_errors))
            if len(c_errors) == 0:
            # if True:
                c_errors = validate_assign_prod_to_claimitems_and_services(claim)
                logger.debug("SubmitClaimsMutation: claim %s assigned, nb of errors: %s", claim_uuid, len(c_errors))
                c_errors += process_dedrem(claim, user.id_for_audit, False)
                logger.debug("SubmitClaimsMutation: claim %s processed for dedrem, nb of errors: %s", claim_uuid,
                             len(errors))
            c_errors += set_claim_forwarded(claim, c_errors, user)
            logger.debug("ForwardClaimsMutation: claim %s set forwarded", claim_uuid)
            if c_errors:
                errors.append({
                    'title': claim.code,
                    'list': c_errors
                })
        if len(errors) == 1:
            errors = errors[0]['list']
        logger.debug("ForwardClaimsMutation: claim done, errors: %s", len(errors))
        return errors

def set_claims_status(uuids, field, status, audit_data=None):
    errors = []
    for claim_uuid in uuids:
        claim = Claim.objects \
            .filter(uuid=claim_uuid,
                    validity_to__isnull=True) \
            .first()
        if claim is None:
            errors += [{'message': _(
                "claim.validation.id_does_not_exist") % {'id': claim_uuid}}]
            continue
        try:
            claim.save_history()
            setattr(claim, field, status)
            if audit_data:
                for k, v in audit_data.items():
                    setattr(claim, k, v)
            claim.save()
        except Exception as exc:
            errors += [
                {'message': _("claim.mutation.failed_to_change_status_of_claim") %
                            {'code': claim.code}}]

    return errors


def update_claims_dedrems(uuids, user):
    # We could do it in one query with filter(claim__uuid__in=uuids) but we'd loose the logging
    errors = []
    for uuid in uuids:
        logger.debug(f"delivering review on {uuid}, reprocessing dedrem ({user})")
        claim = Claim.objects.get(uuid=uuid)
        errors += validate_and_process_dedrem_claim(claim, user, False)
    return errors


class SelectClaimsForFeedbackMutation(OpenIMISMutation):
    """
    Select one or several claims for feedback.
    """
    _mutation_module = "claim"
    _mutation_class = "SelectClaimsForFeedbackMutation"

    class Input(OpenIMISMutation.Input):
        uuids = graphene.List(graphene.String)

    @classmethod
    def async_mutate(cls, user, **data):
        if not user.has_perms(ClaimConfig.gql_mutation_select_claim_feedback_perms):
            raise PermissionDenied(_("unauthorized"))
        return set_claims_status(data['uuids'], 'feedback_status', Claim.STATUS_CHECKED)


class BypassClaimsFeedbackMutation(OpenIMISMutation):
    """
    Bypass feedback for one or several claims
    """
    _mutation_module = "claim"
    _mutation_class = "BypassClaimsFeedbackMutation"

    class Input(OpenIMISMutation.Input):
        uuids = graphene.List(graphene.String)

    @classmethod
    def async_mutate(cls, user, **data):
        if not user.has_perms(ClaimConfig.gql_mutation_bypass_claim_feedback_perms):
            raise PermissionDenied(_("unauthorized"))
        return set_claims_status(data['uuids'], 'feedback_status', Claim.STATUS_VALUATED)


class SkipClaimsFeedbackMutation(OpenIMISMutation):
    """
    Skip feedback for one or several claims
    Skip indicates that the claim is not selected for feedback
    """
    _mutation_module = "claim"
    _mutation_class = "SkipClaimsFeedbackMutation"

    class Input(OpenIMISMutation.Input):
        uuids = graphene.List(graphene.String)

    @classmethod
    def async_mutate(cls, user, **data):
        if not user.has_perms(ClaimConfig.gql_mutation_skip_claim_feedback_perms):
            raise PermissionDenied(_("unauthorized"))
        return set_claims_status(data['uuids'], 'feedback_status', Claim.STATUS_ENTERED)


class DeliverClaimFeedbackMutation(OpenIMISMutation):
    """
    Deliver feedback of a claim
    """
    _mutation_module = "claim"
    _mutation_class = "DeliverClaimFeedbackMutation"

    class Input(OpenIMISMutation.Input):
        claim_uuid = graphene.String(required=False, read_only=True)
        feedback = graphene.Field(FeedbackInputType, required=True)

    @classmethod
    def async_mutate(cls, user, **data):
        claim = None
        try:
            if not user.has_perms(ClaimConfig.gql_mutation_deliver_claim_feedback_perms):
                raise PermissionDenied(_("unauthorized"))
            claim = Claim.objects.select_related('feedback').get(
                uuid=data['claim_uuid'],
                validity_to__isnull=True)
            prev_feedback = claim.feedback
            prev_claim_id = claim.save_history()
            if prev_feedback:
                prev_feedback.claim_id = prev_claim_id
                prev_feedback.save()
            feedback = data['feedback']
            from core.utils import TimeUtils
            feedback['validity_from'] = TimeUtils.now()
            feedback['audit_user_id'] = user.id_for_audit
            # The legacy model has a Foreign key on both sides of this one-to-one relationship
            f, created = Feedback.objects.update_or_create(
                claim=claim,
                defaults=feedback
            )
            claim.feedback = f
            claim.feedback_status = Claim.FEEDBACK_DELIVERED
            claim.feedback_available = True
            claim.save()
            return None
        except Exception as exc:
            return [{
                'message': _("claim.mutation.failed_to_update_claim") % {'code': claim.code if claim else None},
                'detail': str(exc)}]


class SelectClaimsForReviewMutation(OpenIMISMutation):
    """
    Select one or several claims for review.
    """
    _mutation_module = "claim"
    _mutation_class = "SelectClaimsForReviewMutation"

    class Input(OpenIMISMutation.Input):
        uuids = graphene.List(graphene.String)

    @classmethod
    def async_mutate(cls, user, **data):
        if not user.has_perms(ClaimConfig.gql_mutation_select_claim_review_perms):
            raise PermissionDenied(_("unauthorized"))
        return set_claims_status(data['uuids'], 'review_status', Claim.STATUS_CHECKED)


class BypassClaimsReviewMutation(OpenIMISMutation):
    """
    Bypass review for one or several claims
    Bypass indicates that review of a previously selected claim won't be delivered
    """
    _mutation_module = "claim"
    _mutation_class = "BypassClaimsReviewMutation"

    class Input(OpenIMISMutation.Input):
        uuids = graphene.List(graphene.String)

    @classmethod
    def async_mutate(cls, user, **data):
        if not user.has_perms(ClaimConfig.gql_mutation_bypass_claim_review_perms):
            raise PermissionDenied(_("unauthorized"))
        return set_claims_status(data['uuids'], 'review_status', Claim.STATUS_VALUATED)


class DeliverClaimsReviewMutation(OpenIMISMutation):
    """
    Mark claim review as delivered for one or several claims
    """
    _mutation_module = "claim"
    _mutation_class = "DeliverClaimsReviewMutation"

    class Input(OpenIMISMutation.Input):
        uuids = graphene.List(graphene.String)

    @classmethod
    def async_mutate(cls, user, **data):
        logger.error("SaveClaimReviewMutation")
        if not user.has_perms(ClaimConfig.gql_mutation_deliver_claim_review_perms):
            raise PermissionDenied(_("unauthorized"))

        errors = set_claims_status(data['uuids'], 'review_status', Claim.REVIEW_DELIVERED,
                                   {'audit_user_id_review': user.id_for_audit})
        # setattr(data['uuids'], 'review_status', Claim.REVIEW_DELIVERED)
        # OMT-208 update the dedrem for the reviewed claims
        errors += update_claims_dedrems(data["uuids"], user)

        return errors


class SkipClaimsReviewMutation(OpenIMISMutation):
    """
    Skip review for one or several claims
    Skip indicates that the claim is not selected for review
    """
    _mutation_module = "claim"
    _mutation_class = "SkipClaimsReviewMutation"

    class Input(OpenIMISMutation.Input):
        uuids = graphene.List(graphene.String)

    @classmethod
    def async_mutate(cls, user, **data):
        if not user.has_perms(ClaimConfig.gql_mutation_skip_claim_review_perms):
            raise PermissionDenied(_("unauthorized"))
        return set_claims_status(data['uuids'], 'review_status', Claim.STATUS_ENTERED)


class SaveClaimReviewMutation(OpenIMISMutation):
    """
    Save the review of a claim (items and services)
    """
    _mutation_module = "claim"
    _mutation_class = "SaveClaimReviewMutation"

    class Input(OpenIMISMutation.Input):
        claim_uuid = graphene.String(required=False, read_only=True)
        adjustment = graphene.String(required=False)
        check_remarks = graphene.String(required=False)
        check_attachment = graphene.String(required=False)
        scheme_app_id = graphene.String(required=False)
        subProduct_id = graphene.Int(required=False)
        capability = graphene.String(required=False)
        items = graphene.List(ClaimItemInputType, required=False)
        services = graphene.List(ClaimServiceInputType, required=False)

    @classmethod
    def async_mutate(cls, user, **data):
        try:
            if not user.has_perms(ClaimConfig.gql_mutation_deliver_claim_review_perms):
                raise PermissionDenied(_("unauthorized"))
            claim = Claim.objects.get(uuid=data['claim_uuid'],
                                      validity_to__isnull=True)
            if claim is None:
                return [{'message': _(
                    "claim.validation.id_does_not_exist") % {'id': data['claim_uuid']}}]
            claim.save_history()
            claim.adjustment = data.get('adjustment', None)
            claim.check_remarks = data.get('check_remarks', None)
            claim.check_attachment = data.get('check_attachment', None)
            claim.scheme_app_id = data.get('scheme_app_id', None)
            if claim.product_id == 1:
                claim.subProduct_id = data.get('subProduct_id', None)
            claim.capability = data.get('capability',None)
            items = data.pop('items') if 'items' in data else []
            all_rejected = True

            for item in items:
                item_id = item.pop('id')
                claim.items.filter(id=item_id).update(**item)
                if item['status'] == ClaimItem.STATUS_PASSED:
                    all_rejected = False
            services = data.pop('services') if 'services' in data else []
            for service in services:
                service_id = service.pop('id')
                claim.services.filter(id=service_id).update(**service)
                if service['status'] == ClaimService.STATUS_PASSED:
                    all_rejected = False
            claim.approved = approved_amount(claim)
            claim.audit_user_id_review = user.id_for_audit
            # if all_rejected:
            #     claim.status = Claim.STATUS_REJECTED
            claim.save()
            return None
        except Exception as exc:
            return [{
                'message': _("claim.mutation.failed_to_update_claim") % {'code': claim.code},
                'detail': str(exc)}]


class ProcessClaimsMutation(OpenIMISMutation):
    """
    Process one or several claims.
    """
    _mutation_module = "claim"
    _mutation_class = "ProcessClaimsMutation"

    class Input(OpenIMISMutation.Input):
        uuids = graphene.List(graphene.String)

    @classmethod
    def async_mutate(cls, user, **data):
        if not user.has_perms(ClaimConfig.gql_mutation_process_claims_perms):
            raise PermissionDenied(_("unauthorized"))
        errors = []
        for claim_uuid in data["uuids"]:
            logger.debug("ProcessClaimsMutation: processing %s", claim_uuid)
            c_errors = []
            claim = Claim.objects \
                .filter(uuid=claim_uuid) \
                .prefetch_related("items") \
                .prefetch_related("services") \
                .first()
            if claim is None:
                errors += {
                    'title': claim_uuid,
                    'list': [{'message': _(
                        "claim.validation.id_does_not_exist") % {'id': claim_uuid}}]
                }
                continue
            claim.save_history()
            claim.audit_user_id_process = user.id_for_audit
            entryby_user = get_user_by_userId(claim.audit_user_id)
            recommend_user = get_user_by_userId(claim.audit_user_id_review)
            if entryby_user and recommend_user:
                logger.debug("ProcessClaimsMutation: validating claim %s", claim_uuid)
                c_errors += PostClaimForPayment(user, claim_uuid,entryby_user,recommend_user)
                if not c_errors:
                    c_errors += validate_and_process_dedrem_claim(claim, user, True)
                    c_errors += set_claim_processed_or_valuated(claim, c_errors, user)
                    logger.debug("ProcessClaimsMutation: claim %s set processed or valuated", claim_uuid)
            else:
                errors += {
                    'title': claim_uuid,
                    'list': [{'message': _(
                        "claim.validation.audit_user_not_found") % {'id': claim_uuid}}]
                }
            if c_errors:
                errors.append({
                    'title': claim.code,
                    'list': c_errors
                })


        if len(errors) == 1:
            errors = errors[0]['list']
        logger.debug("ProcessClaimsMutation: claims %s done, errors: %s", data["uuids"], len(errors))
        return errors
import os
def PostClaimForPayment(user,claim_uuid,entryby_user,recommend_user):
    errors = []
    claim = Claim.objects \
            .filter(uuid=claim_uuid) \
            .first()
    try:
        base_url = os.getenv("BASE_API_URL")
        # url1 = "https://localhost:44379/api/auth/login"
        logger.debug("Post Claim For payment: getting Token %s", claim_uuid)

        url = base_url + str("auth/login")
        payload = "{\n\t'UserId':'% s',\n\t'Password':'% s',\n\t'wsType':'% s'\n}" % (os.getenv("API_USER"), os.getenv("API_PASSWORD"), os.getenv("API_WSTYPE"))
        headers = {
            'Content-Type': 'application/json'
        }
        response = requests.request("POST", url, headers=headers, data=payload, verify=False)
        if response.ok:
            token = response.json()
            logger.debug("Post Claim For payment: Preparing JSON for payment POST %s", claim_uuid)

            payment_api="health/PostClaimStatement/"
            url = base_url+str(payment_api)
            filter_chfid = ''.join(filter(lambda i: i.isdigit(), claim.insuree.chf_id))
            a = {
                    "SSFID": filter_chfid,
                    "SCHAPPID": '1' if claim.product.code == 'SSF0001' else '2',
                    "SCHID": claim.subProduct.id,
                    "ClaimAppDate": claim.date_claimed.strftime('%Y.%m.%d'),
                    "EntryDate": datetime.now().strftime('%Y.%m.%d'),
                    "RStatus": "V",
                    "ApprovedAmount": str(claim.approved) ,
                    "ApprovedBy": recommend_user[2],#UserID FullName LoginName RoleName
                    "ApprovedDate": datetime.now().strftime('%Y.%m.%d'),
                    "ClaimAmount": str(claim.claimed),
                    "ClaimDate": claim.date_claimed.strftime('%Y.%m.%d'),
                    "ClaimId":claim.code,
                    "HCode":claim.health_facility.code,
                    "RecommendedBy":recommend_user[2],
                    "RecommendedByPost":recommend_user[3],
                    "EntryByPost" :entryby_user[3],
                    "EntryBy":entryby_user[2],
                    "EntryByFullName":entryby_user[1],
                    "DischargeDate":claim.date_to.strftime('%Y.%m.%d') if claim.date_to else claim.date_from.strftime('%Y.%m.%d'),
                    "AdmitDate": claim.date_from.strftime('%Y.%m.%d'),
                    "PayTo": claim.pay_to if claim.pay_to else 1
                }

            # if(claim.product.code == 'SSF0001'):
            print('Json Dibya',claim.hf_branch_id)
            a["BankId"]=claim.hf_bank.BankId
            a["BankBranchId"]=claim.hf_branch.CIPSBranchId
            a["AccountName"]=claim.hf_account_name
            a["AccountNumber"]=claim.hf_account_number
            payload = json.dumps(a)
            logger.debug("Post Claim For payment: Requesting  %s", claim_uuid)
            headers = {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token["token"]
            }
            response = requests.request("POST", url, headers=headers, data=payload,verify=False)
            logger.debug("Post Claim For payment: Request Response for  %s :%s", claim_uuid,response)
            print(response,'response')
            if response.ok:
                print('payment Response',response.json())
            else:
                raise Exception('Fail to Post Payment '+str(response.json()))
        else:
            raise Exception('Fail to Post Payment '+str(response.json()))
    except Exception as e:
        logger.error(str(e))
        print('Exception dibya',e)
        claim.save()
        errors += {str(e)}
    return errors



class DeleteClaimsMutation(OpenIMISMutation):
    """
    Mark one or several claims as Deleted (validity_to)
    """

    class Input(OpenIMISMutation.Input):
        uuids = graphene.List(graphene.String)

    _mutation_module = "claim"
    _mutation_class = "DeleteClaimsMutation"

    @classmethod
    def async_mutate(cls, user, **data):
        if not user.has_perms(ClaimConfig.gql_mutation_delete_claims_perms):
            raise PermissionDenied(_("unauthorized"))
        errors = []
        for claim_uuid in data["uuids"]:
            claim = Claim.objects \
                .filter(uuid=claim_uuid) \
                .prefetch_related("items") \
                .prefetch_related("services") \
                .first()
            if claim is None:
                errors += {
                    'title': claim_uuid,
                    'list': [{'message': _(
                        "claim.validation.id_does_not_exist") % {'id': claim_uuid}}]
                }
                continue
            errors += set_claim_deleted(claim)
        if len(errors) == 1:
            errors = errors[0]['list']
        return errors


def set_claim_submitted(claim, errors, user):
    try:
        claim.audit_user_id_submit = user.id_for_audit
        if errors:
            claim.status = Claim.STATUS_REJECTED
        else:
            claim.approved = approved_amount(claim)
            claim.status =Claim.STATUS_RECOMMENDED if  (claim.product.code == "SSF0001") else Claim.STATUS_CHECKED
            from core.utils import TimeUtils
            claim.submit_stamp = TimeUtils.now()
            claim.category = get_claim_category(claim)
        claim.save()
        return []
    except Exception as exc:
        return {
            'title': claim.code,
            'list': [{
                'message': _("claim.mutation.failed_to_change_status_of_claim") % {'code': claim.code},
                'detail': claim.uuid}]
        }

def set_claim_forwarded(claim, errors, user):
    try:
        # claim.audit_user_id_forward = user.id_for_audit
        if errors:
            claim.status = Claim.STATUS_REJECTED
        else:
            # claim.approved = approved_amount(claim)
            claim.status = Claim.STATUS_FORWARDED
            claim.review_status = Claim.REVIEW_IDLE
            from core.utils import TimeUtils
            # claim.forward_stamp = TimeUtils.now()
        claim.save()
        return []
    except Exception as exc:
        return {
            'title': claim.code,
            'list': [{
                'message': _("claim.mutation.failed_to_change_status_of_claim") % {'code': claim.code},
                'detail': claim.uuid}]
        }

def set_claim_deleted(claim):
    try:
        claim.delete_history()
        return []
    except Exception as exc:
        return {
            'title': claim.code,
            'list': [{
                'message': _("claim.mutation.failed_to_change_status_of_claim") % {'code': claim.code},
                'detail': claim.uuid}]
        }


def details_with_relative_prices(details):
    return details.filter(status=ClaimDetail.STATUS_PASSED) \
        .filter(price_origin=ProductItemOrService.ORIGIN_RELATIVE) \
        .exists()


def with_relative_prices(claim):
    return details_with_relative_prices(claim.items) or details_with_relative_prices(claim.services)


def set_claim_processed_or_valuated(claim, errors, user):
    try:
        if errors:
            claim.status = Claim.STATUS_REJECTED
        else:
            claim.status = Claim.STATUS_PROCESSED if with_relative_prices(claim) else Claim.STATUS_VALUATED
            claim.audit_user_id_process = user.id_for_audit
            from core.utils import TimeUtils
            claim.process_stamp = TimeUtils.now()
        claim.save()
        return []
    except Exception as ex:
        return {
            'title': claim.code,
            'list': [{'message': _("claim.mutation.failed_to_change_status_of_claim") % {'code': claim.code},
                      'detail': claim.uuid}]
        }


def validate_and_process_dedrem_claim(claim, user, is_process):
    errors = validate_claim(claim, False)
    logger.debug("ProcessClaimsMutation: claim %s validated, nb of errors: %s", claim.uuid, len(errors))
    if len(errors) == 0:
        errors = validate_assign_prod_to_claimitems_and_services(claim)
        logger.debug("ProcessClaimsMutation: claim %s assigned, nb of errors: %s", claim.uuid, len(errors))
        errors += process_dedrem(claim, user.id_for_audit, is_process)
        logger.debug("ProcessClaimsMutation: claim %s processed for dedrem, nb of errors: %s", claim.uuid,
                     len(errors))
    else:
        # OMT-208 the claim is invalid. If there is a dedrem, we need to clear it (caused by a review)
        deleted_dedrems = ClaimDedRem.objects.filter(claim=claim).delete()
        if deleted_dedrems:
            logger.debug(f"Claim {claim.uuid} is invalid, we deleted its dedrem ({deleted_dedrems})")
    if is_process:
        errors += set_claim_processed_or_valuated(claim, errors, user)
    return []
