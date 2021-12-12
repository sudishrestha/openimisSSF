import uuid

from claim_batch import models as claim_batch_models
from core import fields
from core import models as core_models
from django import dispatch
from django.conf import settings
from django.db import models
from django.utils.translation.template import blankout
from graphql import ResolveInfo
from insuree import models as insuree_models
from location import models as location_models
from location.models import UserDistrict
from medical import models as medical_models
from numpy.distutils.system_info import blas_info
from numpy.lib.nanfunctions import _divide_by_count
from policy import models as policy_models
from product import models as product_models
from sosys.models import Employer, Bank, BankBranch,ClaimDocumentsMaster,SubProduct
class ClaimAdmin(core_models.VersionedModel):
    id = models.AutoField(db_column='ClaimAdminId', primary_key=True)
    uuid = models.CharField(db_column='ClaimAdminUUID', max_length=36, default=uuid.uuid4, unique=True)

    code = models.CharField(db_column='ClaimAdminCode', max_length=25, blank=True, null=True)
    last_name = models.CharField(db_column='LastName', max_length=100, blank=True, null=True)
    other_names = models.CharField(db_column='OtherNames', max_length=100, blank=True, null=True)
    dob = models.DateField(db_column='DOB', blank=True, null=True)
    email_id = models.CharField(db_column='EmailId', max_length=200, blank=True, null=True)
    phone = models.CharField(db_column='Phone', max_length=50, blank=True, null=True)
    health_facility = models.ForeignKey(
        location_models.HealthFacility, models.DO_NOTHING, db_column='HFId', blank=True, null=True)
    has_login = models.BooleanField(db_column='HasLogin', blank=True, null=True)

    audit_user_id = models.IntegerField(db_column='AuditUserId', blank=True, null=True)
    # row_id = models.BinaryField(db_column='RowId', blank=True, null=True)

    def __str__(self):
        return self.code + " " + self.last_name + " " + self.other_names

    @classmethod
    def get_queryset(cls, queryset, user):
        queryset = cls.filter_queryset(queryset)
        # GraphQL calls with an info object while Rest calls with the user itself
        if isinstance(user, ResolveInfo):
            user = user.context.user
        if settings.ROW_SECURITY and user.is_anonymous:
            return queryset.filter(id=-1)
        if settings.ROW_SECURITY:
            dist = UserDistrict.get_user_districts(user._u)
            return queryset.filter(
                health_facility__location_id__in=[l.location_id for l in dist]
            )
        return queryset


    class Meta:
        managed = False
        db_table = 'tblClaimAdmin'


class Feedback(core_models.VersionedModel):
    id = models.AutoField(db_column='FeedbackID', primary_key=True)
    uuid = models.CharField(db_column='FeedbackUUID', max_length=36, default=uuid.uuid4, unique=True)
    claim = models.OneToOneField(
        "Claim", models.DO_NOTHING, db_column='ClaimID', blank=True, null=True, related_name="+")
    care_rendered = models.NullBooleanField(db_column='CareRendered', blank=True, null=True)
    payment_asked = models.NullBooleanField(db_column='PaymentAsked', blank=True, null=True)
    drug_prescribed = models.NullBooleanField(db_column='DrugPrescribed', blank=True, null=True)
    drug_received = models.NullBooleanField(db_column='DrugReceived', blank=True, null=True)
    asessment = models.SmallIntegerField(db_column='Asessment', blank=True, null=True)
    # No FK in database (so value may not be an existing officer.id !)
    officer_id = models.IntegerField(db_column='CHFOfficerCode', blank=True, null=True)
    feedback_date = fields.DateTimeField(db_column='FeedbackDate', blank=True, null=True)
    audit_user_id = models.IntegerField(db_column='AuditUserID')

    class Meta:
        managed = False
        db_table = 'tblFeedback'

    @classmethod
    def get_queryset(cls, queryset, user):
        queryset = cls.filter_queryset(queryset)
        # GraphQL calls with an info object while Rest calls with the user itself
        if isinstance(user, ResolveInfo):
            user = user.context.user
        if settings.ROW_SECURITY and user.is_anonymous:
            return queryset.filter(id=-1)
        if settings.ROW_SECURITY:
            dist = UserDistrict.get_user_districts(user._u)
            return queryset.filter(
                claim__health_facility__location_id__in=[l.location_id for l in dist]
            )
        return queryset


signal_claim_rejection = dispatch.Signal(providing_args=["claim"])


class Claim(core_models.VersionedModel, core_models.ExtendableModel):
    id = models.AutoField(db_column='ClaimID', primary_key=True)
    uuid = models.CharField(db_column='ClaimUUID',
                            max_length=36, default=uuid.uuid4, unique=True)
    category = models.CharField(
        db_column='ClaimCategory', max_length=1, blank=True, null=True)
    insuree = models.ForeignKey(
        insuree_models.Insuree, models.DO_NOTHING, db_column='InsureeID')
    code = models.CharField(db_column='ClaimCode', max_length=60)
    date_from = fields.DateField(db_column='DateFrom')
    date_to = fields.DateField(db_column='DateTo', blank=True, null=True)
    status = models.SmallIntegerField(db_column='ClaimStatus')
    adjuster = models.ForeignKey(
        core_models.InteractiveUser, models.DO_NOTHING,
        db_column='Adjuster', blank=True, null=True)
    adjustment = models.TextField(
        db_column='Adjustment', blank=True, null=True)
    claimed = models.DecimalField(
        db_column='Claimed',
        max_digits=18, decimal_places=2, blank=True, null=True)
    approved = models.DecimalField(
        db_column='Approved',
        max_digits=18, decimal_places=2, blank=True, null=True)
    reinsured = models.DecimalField(
        db_column='Reinsured',
        max_digits=18, decimal_places=2, blank=True, null=True)
    valuated = models.DecimalField(
        db_column='Valuated', max_digits=18, decimal_places=2, blank=True, null=True)
    date_claimed = fields.DateField(db_column='DateClaimed')
    date_processed = fields.DateField(
        db_column='DateProcessed', blank=True, null=True)
    # Django uses the feedback_id column to create the feedback column, which conflicts with the boolean field
    feedback_available = models.BooleanField(
        db_column='Feedback', default=False)
    feedback = models.OneToOneField(
        Feedback, models.DO_NOTHING,
        db_column='FeedbackID', blank=True, null=True, related_name="+")
    explanation = models.TextField(
        db_column='Explanation', blank=True, null=True)
    feedback_status = models.SmallIntegerField(
        db_column='FeedbackStatus', blank=True, null=True, default=1)
    review_status = models.SmallIntegerField(
        db_column='ReviewStatus', blank=True, null=True, default=1)
    approval_status = models.SmallIntegerField(
        db_column='ApprovalStatus', blank=True, null=True, default=1)
    rejection_reason = models.SmallIntegerField(
        db_column='RejectionReason', blank=True, null=True, default=0)

    batch_run = models.ForeignKey(claim_batch_models.BatchRun,
                                  models.DO_NOTHING, db_column='RunID', blank=True, null=True)
    audit_user_id = models.IntegerField(db_column='AuditUserID')
    validity_from_review = fields.DateTimeField(
        db_column='ValidityFromReview', blank=True, null=True)
    validity_to_review = fields.DateTimeField(
        db_column='ValidityToReview', blank=True, null=True)

    health_facility = models.ForeignKey(
        location_models.HealthFacility, models.DO_NOTHING, db_column='HFID')

    submit_stamp = fields.DateTimeField(
        db_column='SubmitStamp', blank=True, null=True)
    process_stamp = fields.DateTimeField(
        db_column='ProcessStamp', blank=True, null=True)
    remunerated = models.DecimalField(
        db_column='Remunerated', max_digits=18, decimal_places=2, blank=True, null=True)
    guarantee_id = models.CharField(
        db_column='GuaranteeId', max_length=50, blank=True, null=True)
    admin = models.ForeignKey(
        ClaimAdmin, models.DO_NOTHING, db_column='ClaimAdminId',
        blank=True, null=True)
    icd = models.ForeignKey(
        medical_models.Diagnosis, models.DO_NOTHING, db_column='ICDID',
        related_name="claim_icds")
    icd_1 = models.ForeignKey(
        medical_models.Diagnosis, models.DO_NOTHING, db_column='ICDID1',
        related_name="claim_icd1s",
        blank=True, null=True)
    icd_2 = models.ForeignKey(
        medical_models.Diagnosis, models.DO_NOTHING, db_column='ICDID2',
        related_name="claim_icd2s",
        blank=True, null=True)
    icd_3 = models.ForeignKey(
        medical_models.Diagnosis, models.DO_NOTHING, db_column='ICDID3',
        related_name="claim_icd3s",
        blank=True, null=True)
    icd_4 = models.ForeignKey(
        medical_models.Diagnosis, models.DO_NOTHING, db_column='ICDID4',
        related_name="claim_icd4s",
        blank=True, null=True)

    visit_type = models.CharField(
        db_column='VisitType', max_length=1, blank=True, null=True)
    audit_user_id_review = models.IntegerField(
        db_column='AuditUserIDReview', blank=True, null=True)
    audit_user_id_submit = models.IntegerField(
        db_column='AuditUserIDSubmit', blank=True, null=True)
    audit_user_id_process = models.IntegerField(
        db_column='AuditUserIDProcess', blank=True, null=True)
    scheme_type = models.IntegerField(
        db_column='SchemeType', blank=True, null=True)
    # row_id = models.BinaryField(db_column='RowID', blank=True, null=True)
    # Anusuch 2 fields for SSF

    reason_of_sickness = models.CharField(db_column='ReasonOfSickness',blank=True,null=True,max_length=255)
    condition_of_wound = models.CharField(db_column='ConditionOfWound',blank=True,null=True,max_length=1)
    injured_body_part = models.TextField(db_column='InjuredBodyPart',blank=True,null=True)
    is_dead = models.CharField(db_column='IsDead',blank=True,null=True,max_length=5)
    dead_date= models.DateField(db_column='DeadDate',blank=True,null=True)
    dead_time = models.TimeField(db_column='DeadTime',blank=True,null=True)
   # dead_time = models.CharField(db_column='DeadTime',blank=True,null=True, max_length=10)
    dead_reason = models.TextField(db_column='DeadReason',blank=True,null=True)
    dead_certificate_attachment = models.TextField(db_column='DeadCertificateAttachment',null=True,blank=True)
    cancer = models.CharField(db_column='Cancer',null=True,blank=True,max_length=255)
    heart_attack = models.CharField(db_column='HeartAttack',null=True,blank=True,max_length=255)
    hiv = models.CharField(db_column='HIV',null=True,blank=True,max_length=255)
    high_bp = models.CharField(db_column='HighBp',null=True,blank=True,max_length=255)
    diabetes = models.CharField(db_column='Diabetes',null=True,blank=True,max_length=255)
    capability = models.CharField(db_column='Capability',null=True,blank=True,max_length=5)
    accident_description = models.TextField(db_column='AccidentDescription',null=True,blank=True)

    employer = models.ForeignKey(Employer,models.DO_NOTHING,blank=True,null=True,related_name='claim_employer')
    discharge_type = models.CharField(db_column='DischargeType',blank=True,null=True,max_length=30)
    follow_up_date = models.DateField(db_column= 'FollowUpDate',blank=True,null=True)
    rest_period = models.IntegerField(db_column='RestPeriod',blank=True,null=True)#this should be in days

    refer_to_health_facility = models.ForeignKey(location_models.HealthFacility, models.DO_NOTHING, related_name='refer_to_claim' ,null=True,blank=True,db_column='ReferToHealthFacility')
    refer_to_date = fields.DateField(db_column='ReferToDate',null=True,blank=True)
    refer_to_hf_other = models.CharField(db_column='ReferToHFOther',null=True,blank=True,max_length=255)
    discharge_summary = models.TextField(db_column='DischargeSummary',null=True,blank=True)
    # Refer By when visit type is Referral
    refer_from_health_facility = models.ForeignKey(location_models.HealthFacility, models.DO_NOTHING,related_name='refer_from_claim',db_column='ReferFromHealthFacility',null=True,blank=True)
    refer_from_date = models.DateField(db_column='ReferFromDate',null=True,blank=True)
    refer_from_hf_other = models.CharField(db_column='ReferFromHfOther',null=True,blank=True,max_length=255)
    is_admitted = models.CharField(db_column='IsAdmitted',null=True,blank=True,max_length=6)


    refer_by_claim = models.ForeignKey('Claim' ,on_delete=models.DO_NOTHING,related_name='refered_claim',blank=True,null=True)
    refer_flag = models.BooleanField(db_column='ReferFlag',default=False)

    # Hospital Bank Details
    hf_bank  = models.ForeignKey(Bank,on_delete=models.DO_NOTHING,related_name='claim_hf_bank',null=True,blank=True)
    hf_branch = models.ForeignKey(BankBranch,on_delete=models.DO_NOTHING,related_name='claim_hf_branch',null=True,blank=True)
    hf_account_name = models.CharField(max_length=60,null=True,blank=True)
    hf_account_number = models.CharField(max_length=30,null=True,blank=True)

    # Check Remarks, Attachment and Scheme ID
    check_remarks = models.TextField(null=True,blank=True)
    check_attachment = models.TextField(null=True,blank=True)
    scheme_app_id = models.IntegerField(null=True,blank=True)
    subProduct = models.ForeignKey(SubProduct, on_delete=models.DO_NOTHING, related_name="claim_subProduct", null=True,blank=True)
    product = models.ForeignKey(product_models.Product, on_delete=models.DO_NOTHING,related_name='claim_product',null=True,blank=True)
    is_disable = models.CharField(db_column='is_disable',null=True,blank=True,max_length=255)
    is_reclaim = models.CharField(db_column='isReclaim',null=True,blank=True,max_length=6)
    head_claim = models.ForeignKey('self',on_delete=models.DO_NOTHING,related_name='child_claim',null=True,blank=True)
    claim_for = models.IntegerField(null=True, blank=True)
    pay_to = models.IntegerField(db_column="payTo",null=True, blank=True)
    payment_status = models.IntegerField(db_column="paymentStatus",null=True,blank=True,default=0)
    # action status update date
    payment_date = models.DateTimeField(db_column="paymentDate",null=True,blank=True)
    payment_entry_date = models.DateTimeField(db_column="paymentEntryDate",null=True,blank=True)
    #will hold remarks for every action from sosys 
    payment_remarks = models.TextField(db_column="paymentRemarks",null=True,blank=True)
    invoice_no = models.TextField(db_column="invoiceNo",null=True,blank=True)
    class Meta:
        managed = True
        db_table = 'tblClaim'

    STATUS_REJECTED = 1
    STATUS_ENTERED = 2
    STATUS_CHECKED = 4
    STATUS_PROCESSED = 8
    STATUS_RECOMMENDED = 6
    STATUS_FORWARDED = 9
    STATUS_VALUATED = 16

    FEEDBACK_IDLE = 1
    FEEDBACK_NOT_SELECTED = 2
    FEEDBACK_SELECTED = 4
    FEEDBACK_DELIVERED = 8
    FEEDBACK_BYPASSED = 16

    REVIEW_IDLE = 1
    REVIEW_NOT_SELECTED = 2
    REVIEW_SELECTED = 4
    REVIEW_DELIVERED = 8
    REVIEW_BYPASSED = 16

    PAYTO_INSUREE = 1
    PAYTO_HEALTHFACILITY = 2

    PAY_BOOKED = 0
    PAYMENT_REJECTED = 1
    PAYMENT_PAID = 2

    def reject(self, rejection_code):
        updated_items = self.items.filter(validity_to__isnull=True).update(
            rejection_reason=rejection_code)
        updated_services = self.services.filter(
            validity_to__isnull=True).update(rejection_reason=rejection_code)
        signal_claim_rejection.send(sender=self.__class__, claim=self)
        return updated_items + updated_services

    def save_history(self, **kwargs):
        prev_id = super(Claim, self).save_history()
        if prev_id:
            prev_items = []
            for item in self.items.all():
                prev_items.append(item.save_history())
            ClaimItem.objects.filter(
                id__in=prev_items).update(claim_id=prev_id)
            prev_services = []
            for service in self.services.all():
                prev_services.append(service.save_history())
            ClaimService.objects.filter(
                id__in=prev_services).update(claim_id=prev_id)
        return prev_id

    @classmethod
    def get_queryset(cls, queryset, user):
        queryset = Claim.filter_queryset(queryset)
        # GraphQL calls with an info object while Rest calls with the user itself
        if isinstance(user, ResolveInfo):
            user = user.context.user
        if settings.ROW_SECURITY and user.is_anonymous:
            return queryset.filter(id=-1)
        if settings.ROW_SECURITY:
            # TechnicalUsers don't have health_facility_id attribute
            if hasattr(user._u, 'health_facility_id') and user._u.health_facility_id:
                return queryset.filter(
                    health_facility_id=user._u.health_facility_id
                )
            else:
                dist = UserDistrict.get_user_districts(user._u)
                return queryset.filter(
                    health_facility__location_id__in=[l.location_id for l in dist]
                )
        return queryset


class ClaimAttachmentsCount(models.Model):
    claim = models.OneToOneField(Claim, primary_key=True, related_name='attachments_count', on_delete=models.DO_NOTHING)
    value = models.IntegerField(db_column='attachments_count')

    class Meta:
        managed = False
        db_table = 'claim_ClaimAttachmentsCountView'


class ClaimMutation(core_models.UUIDModel):
    claim = models.ForeignKey(Claim, models.DO_NOTHING,
                              related_name='mutations')
    mutation = models.ForeignKey(
        core_models.MutationLog, models.DO_NOTHING, related_name='claims')

    class Meta:
        managed = True
        db_table = "claim_ClaimMutation"


class ClaimDetailManager(models.Manager):

    def filter(self, *args, **kwargs):
        keys = [x for x in kwargs if "itemsvc" in x]
        for key in keys:
            new_key = key.replace("itemsvc", self.model.model_prefix)
            kwargs[new_key] = kwargs.pop(key)
        return super(ClaimDetailManager, self).filter(*args, **kwargs)


class ClaimDetail:
    STATUS_PASSED = 1
    STATUS_REJECTED = 2

    objects = ClaimDetailManager()

    @property
    def itemsvc(self):
        if hasattr(self, "item"):
            return self.item
        elif hasattr(self, "service"):
            return self.service
        else:
            raise Exception("ClaimDetail has neither item nor service")

    class Meta:
        abstract = True


class SSFScheme(models.Model):
    id = models.AutoField(db_column='SCH_ID', primary_key=True)
    SCH_NAME= models.CharField(db_column='SCH_NAME',max_length = 100)
    SCH_NAME_ENG= models.CharField(db_column='SCH_NAME_ENG',max_length = 100)
    VISIT_TYPE= models.CharField(db_column='VISIT_TYPE',max_length = 150)
    ENTRY_BY=models.CharField(db_column='ENTRY_BY',max_length = 10)
    ENTRY_DATE=models.BooleanField(db_column='ENTRY_DATE',default =False)
    R_STATUS=models.DateTimeField(db_column='R_STATUS', blank=True, null=True)
    SCHAPP_ID = models.IntegerField(db_column='SCHAPP_ID', blank=True, null=True)
    class Meta:
        db_table = "tblSSFSchemes"
    @classmethod
    def get_queryset(cls, queryset, user):
        queryset = SSFScheme.filter_queryset(queryset)
        return SSFScheme


class ClaimItem(core_models.VersionedModel, ClaimDetail):
    model_prefix = "item"
    id = models.AutoField(db_column='ClaimItemID', primary_key=True)
    claim = models.ForeignKey(Claim, models.DO_NOTHING,
                              db_column='ClaimID', related_name='items')
    item = models.ForeignKey(
        medical_models.Item, models.DO_NOTHING, db_column='ItemID')
    product = models.ForeignKey(product_models.Product,
                                models.DO_NOTHING, db_column='ProdID',
                                blank=True, null=True,
                                related_name="claim_items")
    status = models.SmallIntegerField(db_column='ClaimItemStatus')
    availability = models.BooleanField(db_column='Availability')
    qty_provided = models.DecimalField(
        db_column='QtyProvided', max_digits=18, decimal_places=2)
    qty_approved = models.DecimalField(
        db_column='QtyApproved', max_digits=18, decimal_places=2, blank=True, null=True)
    price_asked = models.DecimalField(
        db_column='PriceAsked', max_digits=18, decimal_places=2)
    price_adjusted = models.DecimalField(
        db_column='PriceAdjusted', max_digits=18, decimal_places=2, blank=True, null=True)
    price_approved = models.DecimalField(
        db_column='PriceApproved', max_digits=18, decimal_places=2, blank=True, null=True)
    price_valuated = models.DecimalField(
        db_column='PriceValuated', max_digits=18, decimal_places=2, blank=True, null=True)
    explanation = models.TextField(
        db_column='Explanation', blank=True, null=True)
    justification = models.TextField(
        db_column='Justification', blank=True, null=True)
    rejection_reason = models.SmallIntegerField(
        db_column='RejectionReason', blank=True, null=True)
    audit_user_id = models.IntegerField(db_column='AuditUserID')
    validity_from_review = fields.DateTimeField(
        db_column='ValidityFromReview', blank=True, null=True)
    validity_to_review = fields.DateTimeField(
        db_column='ValidityToReview', blank=True, null=True)
    audit_user_id_review = models.IntegerField(
        db_column='AuditUserIDReview', blank=True, null=True)
    limitation_value = models.DecimalField(
        db_column='LimitationValue', max_digits=18, decimal_places=2, blank=True, null=True)
    limitation = models.CharField(
        db_column='Limitation', max_length=1, blank=True, null=True)
    policy = models.ForeignKey(
        policy_models.Policy, models.DO_NOTHING, db_column='PolicyID', blank=True, null=True)
    remunerated_amount = models.DecimalField(
        db_column='RemuneratedAmount', max_digits=18, decimal_places=2, blank=True, null=True)
    deductable_amount = models.DecimalField(
        db_column='DeductableAmount', max_digits=18, decimal_places=2, blank=True, null=True)
    exceed_ceiling_amount = models.DecimalField(
        db_column='ExceedCeilingAmount', max_digits=18, decimal_places=2, blank=True, null=True)
    price_origin = models.CharField(
        db_column='PriceOrigin', max_length=1, blank=True, null=True)
    exceed_ceiling_amount_category = models.DecimalField(
        db_column='ExceedCeilingAmountCategory', max_digits=18, decimal_places=2, blank=True, null=True)
    objects = ClaimDetailManager()

    class Meta:
        managed = False
        db_table = 'tblClaimItems'


class ClaimAttachment(core_models.UUIDModel, core_models.UUIDVersionedModel):
    claim = models.ForeignKey(
        Claim, models.DO_NOTHING, related_name='attachments')
    type = models.TextField(blank=True, null=True)
    title = models.TextField(blank=True, null=True)
    date = fields.DateField(blank=True, null=True)
    filename = models.TextField(blank=True, null=True)
    mime = models.TextField(blank=True, null=True)
    # frontend contributions may lead to externalized (nas) storage for documents
    url = models.TextField(blank=True, null=True)
    # Support of BinaryField is database-related: prefer to stick to b64-encoded
    document = models.TextField(blank=True, null=True)
    masterDocument = models.ForeignKey(ClaimDocumentsMaster,on_delete=models.DO_NOTHING,blank=True,null=True)
    documentFrom = models.CharField(max_length=1,blank=True,null=True)
    class Meta:
        managed = True
        db_table = "claim_ClaimAttachment"


class ClaimService(core_models.VersionedModel, ClaimDetail):
    model_prefix = "service"
    id = models.AutoField(db_column='ClaimServiceID', primary_key=True)
    claim = models.ForeignKey(
        Claim, models.DO_NOTHING, db_column='ClaimID', related_name='services')
    service = models.ForeignKey(
        medical_models.Service, models.DO_NOTHING, db_column='ServiceID')
    product = models.ForeignKey(product_models.Product,
                                models.DO_NOTHING, db_column='ProdID',
                                blank=True, null=True,
                                related_name="claim_services")
    status = models.SmallIntegerField(db_column='ClaimServiceStatus')
    qty_provided = models.DecimalField(
        db_column='QtyProvided', max_digits=18, decimal_places=2)
    qty_approved = models.DecimalField(
        db_column='QtyApproved', max_digits=18, decimal_places=2, blank=True, null=True)
    price_asked = models.DecimalField(
        db_column='PriceAsked', max_digits=18, decimal_places=2)
    price_adjusted = models.DecimalField(
        db_column='PriceAdjusted', max_digits=18, decimal_places=2, blank=True, null=True)
    price_approved = models.DecimalField(
        db_column='PriceApproved', max_digits=18, decimal_places=2, blank=True, null=True)
    price_valuated = models.DecimalField(
        db_column='PriceValuated', max_digits=18, decimal_places=2, blank=True, null=True)
    explanation = models.TextField(
        db_column='Explanation', blank=True, null=True)
    justification = models.TextField(
        db_column='Justification', blank=True, null=True)
    rejection_reason = models.SmallIntegerField(
        db_column='RejectionReason', blank=True, null=True)
    audit_user_id = models.IntegerField(db_column='AuditUserID')
    validity_from_review = fields.DateTimeField(
        db_column='ValidityFromReview', blank=True, null=True)
    validity_to_review = fields.DateTimeField(
        db_column='ValidityToReview', blank=True, null=True)
    audit_user_id_review = models.IntegerField(
        db_column='AuditUserIDReview', blank=True, null=True)
    limitation_value = models.DecimalField(
        db_column='LimitationValue', max_digits=18, decimal_places=2, blank=True, null=True)
    limitation = models.CharField(
        db_column='Limitation', max_length=1, blank=True, null=True)
    policy = models.ForeignKey(
        policy_models.Policy, models.DO_NOTHING, db_column='PolicyID', blank=True, null=True)
    remunerated_amount = models.DecimalField(
        db_column='RemuneratedAmount', max_digits=18, decimal_places=2, blank=True, null=True)
    deductable_amount = models.DecimalField(
        db_column='DeductableAmount', max_digits=18, decimal_places=2, blank=True, null=True)
    exceed_ceiling_amount = models.DecimalField(
        db_column='ExceedCeilingAmount', max_digits=18, decimal_places=2, blank=True, null=True)
    price_origin = models.CharField(
        db_column='PriceOrigin', max_length=1, blank=True, null=True)
    exceed_ceiling_amount_category = models.DecimalField(
        db_column='ExceedCeilingAmountCategory', max_digits=18, decimal_places=2, blank=True, null=True)
    objects = ClaimDetailManager()

    class Meta:
        managed = False
        db_table = 'tblClaimServices'


class ClaimDedRem(core_models.VersionedModel):
    id = models.AutoField(db_column='ExpenditureID', primary_key=True)

    policy = models.ForeignKey('policy.Policy', models.DO_NOTHING, db_column='PolicyID', blank=True, null=True,
                               related_name='claim_ded_rems')
    insuree = models.ForeignKey('insuree.Insuree', models.DO_NOTHING, db_column='InsureeID', blank=True, null=True,
                                related_name='claim_ded_rems')
    claim = models.ForeignKey(to=Claim, db_column='ClaimID', db_index=True, related_name="dedrems",
                              on_delete=models.DO_NOTHING)
    ded_g = models.DecimalField(db_column='DedG', max_digits=18, decimal_places=2, blank=True, null=True)
    ded_op = models.DecimalField(db_column='DedOP', max_digits=18, decimal_places=2, blank=True, null=True)
    ded_ip = models.DecimalField(db_column='DedIP', max_digits=18, decimal_places=2, blank=True, null=True)
    rem_g = models.DecimalField(db_column='RemG', max_digits=18, decimal_places=2, blank=True, null=True)
    rem_op = models.DecimalField(db_column='RemOP', max_digits=18, decimal_places=2, blank=True, null=True)
    rem_ip = models.DecimalField(db_column='RemIP', max_digits=18, decimal_places=2, blank=True, null=True)
    rem_consult = models.DecimalField(db_column='RemConsult', max_digits=18, decimal_places=2, blank=True, null=True)
    rem_surgery = models.DecimalField(db_column='RemSurgery', max_digits=18, decimal_places=2, blank=True, null=True)
    rem_delivery = models.DecimalField(db_column='RemDelivery', max_digits=18, decimal_places=2, blank=True, null=True)
    rem_hospitalization = models.DecimalField(db_column='RemHospitalization', max_digits=18, decimal_places=2,
                                              blank=True, null=True)
    rem_antenatal = models.DecimalField(db_column='RemAntenatal', max_digits=18, decimal_places=2,
                                        blank=True, null=True)

    audit_user_id = models.IntegerField(db_column='AuditUserID')

    class Meta:
        managed = False
        db_table = 'tblClaimDedRem'
