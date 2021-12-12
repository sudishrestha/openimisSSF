from numpy.ma import max
from unicodedata import decimal

from django.db import models
from insuree.models import Gender
# Create your models here.
from django.db import models
from insuree.models import Insuree as Insureee
from datetime import datetime
from location.models import HealthFacility
from product.models import Product
# from claim.models import Claim
from django.conf import settings
import core 
from graphql import ResolveInfo


# Create your models here.
class InsureeEmployer(models.Model):
    id = models.AutoField(primary_key = True)
    employer = models.ForeignKey( 'Employer' ,default = None, on_delete=models.DO_NOTHING,related_name="Emp")
    insuree = models.ForeignKey( Insureee , null=True,blank=True, on_delete=models.DO_NOTHING)
    JoinDate = models.CharField(max_length=10, null=True,blank=True)
    TerminatedDate = models.CharField(max_length=10, null=True,blank=True)
    Post = models.CharField(max_length=200, null=True,blank=True)
    
    def __str__(self):
        return str(self.id)
        # return super().__str__()


class Employer(models.Model):
    E_SSID = models.CharField(max_length=25, primary_key = True)
    EmployerNameNep = models.CharField(max_length=150)
    EmployerNameEng = models.CharField(max_length=150)
    AlertSource = models.CharField(max_length=11)
    AlertSourceVal = models.CharField(max_length=100)
    Status = models.CharField(max_length=1)
    AddressId = models.ForeignKey( 'Address' ,default = None,null=True,blank=True, on_delete=models.DO_NOTHING)
    

    @classmethod
    def filter_queryset(cls, queryset=None):
        if queryset is None:
            queryset = cls.objects.all()
        queryset = queryset.filter()
        return queryset

    @classmethod
    def get_queryset(cls, queryset, user):
        queryset = cls.filter_queryset(queryset)
        # GraphQL calls with an info object while Rest calls with the user itself
        # if isinstance(user, ResolveInfo):
        #     user = user.context.user
        # if settings.ROW_SECURITY and user.is_anonymous:
        #     return queryset.filter(id=-1)
        # TODO: filter visible insurees, but how ?
        # if settings.ROW_SECURITY:
        #     dist = UserDistrict.get_user_districts(user._u)
        #     return queryset.filter(
        #         health_facility__location_id__in=[l.location.id for l in dist]
        #     )
        return queryset

    def __str__(self):
        return str(self.E_SSID)

class Address(models.Model):
    AddressId = models.AutoField(primary_key = True)
    DistrictName = models.CharField(max_length=100)
    VDCName = models.CharField(max_length=100)
    Ward = models.IntegerField()
    ToleNameEng = models.CharField(max_length=100)
    ToleNameNep = models.CharField(max_length=100)
    HouseNumber = models.CharField(max_length=50)
    Status = models.CharField(max_length=1)
    
    def __str__(self):
        return str(self.AddressId)


class Insuree(models.Model):
    p_ssid = models.CharField(max_length=14, primary_key = True)
    f_name_nep = models.CharField(max_length=30)
    m_name_nep = models.CharField(max_length=30)
    l_name_eng = models.CharField(max_length=30)
    f_name_eng = models.CharField(max_length=30)
    m_name_eng = models.CharField(max_length=30)
    l_name_eng = models.CharField(max_length=30)
    dob = models.CharField(max_length=10)
    country_code = models.CharField(max_length=2)
    AddressId = models.ForeignKey( 'Address' ,default = None, on_delete=models.DO_NOTHING, related_name='insurees')
    alert_source = models.CharField(max_length=11)
    alert_source_val = models.CharField(max_length=100)
    image_file = models.ImageField(null=True)
    status = models.CharField(max_length=1)
    BankId = models.IntegerField()
    BranchId = models.IntegerField()
    AccountName = models.CharField(max_length=100)
    AccountNumber = models.CharField(max_length=30)
    BloodGroup = models.CharField(max_length=3)
    # gender = models.ForeignKey(Gender, models.DO_NOTHING, db_column='gender', blank=True, null=True,
    #                            related_name='sosys_insurees')
    gender = models.CharField(max_length=1,blank=True,null=True)
    def __str__(self):
        return str(self.p_ssid)


class Dependent(models.Model):
    DependentId = models.AutoField(primary_key = True)
    p_ssid = models.ForeignKey(Insureee, on_delete=models.CASCADE, related_name='dep_set')
    RelationType = models.CharField(max_length=100)
    f_name_nep = models.CharField(max_length=30)
    m_name_nep = models.CharField(max_length=30)
    l_name_eng = models.CharField(max_length=30)
    f_name_eng = models.CharField(max_length=30)
    m_name_eng = models.CharField(max_length=30)
    l_name_eng = models.CharField(max_length=30)
    BankId = models.IntegerField()
    BranchId = models.IntegerField()
    AccountName = models.CharField(max_length=100)
    AccountNumber = models.CharField(max_length=30)

    def __str__(self):
        return str(self.DependentId)


class Bank(models.Model):
    BankId = models.IntegerField(primary_key = True)
    BankName = models.CharField(max_length=100)
    BankNameEng = models.CharField(max_length=100)
    ShortCode = models.CharField(max_length=20)
    Status = models.CharField(max_length=1)

    def __str__(self):
        return str(self.BankId)


class BankBranchManager(models.Manager):
    pass
class BankBranch(models.Model):
    # Id = models.AutoField(primary_key = True)
    objects = BankBranchManager()
    Bank = models.ForeignKey(Bank,on_delete=models.CASCADE,related_name='branches')
    BranchId = models.IntegerField(primary_key = True)
    CIPSBranchId = models.IntegerField(default=1)
    BranchName = models.CharField(max_length=255)
    BranchNameEng=models.CharField(max_length=255)
    Status=models.CharField(max_length=1)
    def __str__(self):
        return str('Bank Id:{} Branch Id:{}'.format(self.BankId,self.BranchId))
    class Meta:
        unique_together = (("Bank", "BranchId"))


class SubProduct(models.Model):
    id = models.IntegerField(primary_key = True)
    sch_name = models.CharField(max_length=100)
    sch_name_eng = models.CharField(max_length=100)
    status = models.CharField(max_length=1)
    product = models.ForeignKey(Product, related_name="subProduct", on_delete=models.DO_NOTHING)
    type = models.CharField(max_length=1,null=True,blank=True)

# class ClaimHead(models.Model):
#     ClaimNumber = models.DecimalField(primary_key = True, max_digits=14, decimal_places=0)
#     schid = models.ForeignKey('Product', on_delete=models.CASCADE)
#     PSSID = models.ForeignKey('Insuree', on_delete=models.DO_NOTHING)
#     EmployerId = models.ForeignKey('Employer', on_delete=models.DO_NOTz HING)
#     ClaimAppDate = models.CharField(max_length=10)
#     BankId = models.IntegerField()
#     BranchId = models.IntegerField()
#     AccountType = models.CharField(max_length=50,blank=True,default=None, null=True)
#     AccountName = models.CharField(max_length=60)
#     AccountNumber = models.CharField(max_length=30)
#     RecommendedBy = models.CharField(max_length=100,blank=True,default=None, null=True)
#     RecommendedPost = models.CharField(max_length=100,blank=True,default=None, null=True)
#     RecommendedPhone = models.CharField(max_length=100,blank=True,default=None, null=True)
#     RecommendedDate = models.CharField(max_length=10,blank=True,default=None, null=True)
#     EntryBy = models.CharField(max_length = 30)
#     EntryDate = models.CharField(max_length=10)
#     Status = models.CharField(max_length=1)
#     SaveMode = models.CharField(max_length=3,blank=True,default=None, null=True)
#     HCode = models.CharField(max_length=20,blank=True,default=None, null=True)
#     ApprovedBy = models.CharField(max_length=100,blank=True,default=None, null=True)
#     ApprovedAmount = models.DecimalField(max_digits=14, decimal_places=2,blank=True,default=None, null=True)
#     ClaimAmount = models.DecimalField(max_digits=14, decimal_places=2)
#     ApproverPost = models.CharField(max_length=100,blank=True,default=None, null=True)
#     ApprovedDate = models.CharField(max_length=10,blank=True,default=None, null=True)
#     ApproveRemarks = models.CharField(max_length=10,blank=True,default=None, null=True)
#     ApprovalDoc = models.BinaryField(blank=True,default=None, null=True)
#     PAID = models.CharField(max_length= 1,blank=True,default=None, null=True)
#     NatureOfAccident = models.IntegerField(blank=True,default=None, null=True)
#
#     def __str__(self):
#         return str(self.ClaimNumber)
#
# class STB_CLAIM_ANUSUCHI5(models.Model):
#     id = models.AutoField(primary_key = True)
#     ClaimNumber = models.ForeignKey('ClaimHead', on_delete=models.CASCADE)
#     RelativeDisease = models.CharField(max_length=500)
#     AdmitHospital = models.CharField(max_length=1)
#     EmergencyAdmission = models.CharField(max_length=1)
#     HospitalName = models.CharField(max_length=100)
#     HospitalAddress = models.CharField(max_length=100)
#     HospitalPhone = models.CharField(max_length=15)
#     ReasonOfSickness = models.CharField(max_length=100)
#     WorkType = models.CharField(max_length=50)
#     DiseaseCondition = models.CharField(max_length = 10)
#     Disease = models.CharField(max_length=30)
#     InjuredPart = models.CharField(max_length=50)
#     DeadDate = models.CharField(max_length=10)
#     DeadTime = models.CharField(max_length=10)
#     DateType = models.CharField(max_length=2)
#
#     def __str__(self):
#         return str(self.ClaimNumber)
#
# class STB_CLAIM_ANUSUCHI4(models.Model):
#     id = models.AutoField(primary_key = True)
#     ClaimNumber = models.ForeignKey('ClaimHead', on_delete=models.CASCADE)
#     BenificieryName = models.CharField(max_length=100)
#     Capacity = models.CharField(max_length=10)
#     PresentAfterAccident = models.CharField(max_length=1)
#     RelativeDisease = models.CharField(max_length=500)
#     WitnessName = models.CharField(max_length=50)
#     AdmitHospital = models.CharField(max_length=1)
#     EmergencyAdmission = models.CharField(max_length=1)
#     HospitalName = models.CharField(max_length=100)
#     HospitalAddress = models.CharField(max_length=100)
#     HospitalPhone = models.CharField(max_length=15)
#     ReasonOfSickness = models.CharField(max_length=100)
#     WorkStaTimeBefAcc = models.CharField(max_length=10)
#     WoundCondition = models.CharField(max_length = 20)
#     EventPlace = models.CharField(max_length=20)
#     ToolDescription = models.CharField(max_length=1000)
#     Work = models.CharField(max_length=50)
#     EventDescription = models.CharField(max_length=1000)
#     WorkerCondition = models.CharField(max_length=20)
#     InjuredPart = models.CharField(max_length=30)
#     EventDate = models.CharField(max_length=10)
#     EventTime = models.CharField(max_length=10)
#     WorkShift = models.CharField(max_length=10)
#     InformDate = models.CharField(max_length=10)
#     LastPresentDate = models.CharField(max_length=10)
#     ReturnDate = models.CharField(max_length=10)
#     WoundTime = models.CharField(max_length=10)
#     LeaveStartDate = models.CharField(max_length=10)
#     LeaveEndDate = models.CharField(max_length=10)
#     SalaryCalBy = models.CharField(max_length=10)
#     DeadDate = models.CharField(max_length=10)
#     DeadTime = models.CharField(max_length=10)
#     DateType = models.CharField(max_length=2)
#
#
#     def __str__(self):
#         return str(self.ClaimNumber)
#
#
# class STB_CLAIM_DOCUMENT(models.Model):
#     DocId = models.IntegerField()
#     ClaimNumber = models.ForeignKey('ClaimHead', on_delete=models.CASCADE)
#     File = models.BinaryField()
#
#     def __str__(self):
#         return str(self.ClaimNumber)
#
#
# class STB_CLAIM_ANUSUCHI2(models.Model):
#     Id = models.AutoField(primary_key=True)
#     ClaimNumber = models.ForeignKey('ClaimHead', on_delete=models.CASCADE,related_name='claim_anusuchi_head')
#     DoctorName = models.CharField(max_length=50)
#     HFAdmissionReason = models.CharField(max_length=8)
#     HFAdmissionReasonOther = models.CharField(max_length=30)
#     ReferralCase = models.BooleanField()
#     TypeOfSickness = models.CharField(max_length=100)
#     RegularCheckup = models.BooleanField()
#     AppointmentCharge = models.DecimalField(decimal_places=2,max_digits=10)
#     HFAdmissionDays = models.IntegerField()
#     HFAdmissionPerDayCharge = models.DecimalField(decimal_places=2,max_digits=10)
#     TestCharge = models.DecimalField(decimal_places=2,max_digits=10)
#     MedicineExpense = models.DecimalField(decimal_places=2,max_digits=10)
#     OtherExpense = models.DecimalField(decimal_places=2,max_digits=10)
#     TotalPaidByContributor = models.DecimalField(decimal_places=2,max_digits=10)
#
#
# class STB_ANUSUCHI2_COMPONENT(models.Model):
#     Id = models.AutoField(primary_key=True)
#     Claim = models.ForeignKey('STB_CLAIM_ANUSUCHI2', on_delete=models.CASCADE, related_name='claim_component_head')
#     Content = models.CharField(max_length=200)
#     SeqNo = models.IntegerField()
#
#     def save(self):
#         entry_count = STB_ANUSUCHI2_COMPONENT\
#                         .objects\
#                         .select_for_update(nowait=True)\
#                         .filter(ClaimNumber=self.ClaimNumber)\
#                         .count()
#         self.SeqNo = entry_count + 1
#         super(STB_ANUSUCHI2_COMPONENT, self).save()

class ClaimRecommend(models.Model):
    id = models.AutoField(primary_key=True)
    claim = models.OneToOneField('claim.Claim', on_delete=models.DO_NOTHING, related_name='claim_recommendation')
    recommender_ssid = models.CharField(max_length=14,null=True,blank=True)
    recommender_post = models.CharField(max_length=50,null=True,blank=True)
    recommender_name = models.CharField(max_length=100,null=True,blank=True)
    recommender_contact = models.CharField(max_length=14,null=True,blank=True)
    recommend_date = models.CharField(max_length=10,null=True,blank=True)
    recommend_remarks = models.CharField(max_length=100,null=True,blank=True)
    recommend_attachment = models.TextField(null=True,blank=True)
    witness_name = models.CharField(max_length=100, null=True,blank=True)
    capacity = models.CharField(max_length=20, null=True,blank=True)
    present_after_case = models.BooleanField(default=False)
    last_present_date = models.CharField(max_length=10,null=True,blank=True)
    present_after_acc_date = models.CharField(max_length=10,null=True,blank=True)
    present_before_app = models.BooleanField(default=False)
    acc_date = models.DateField(null=True,blank=True)
    acc_time = models.TimeField(null=True,blank=True)
    work_shift = models.CharField(max_length=16,null=True,blank=True)
    inform_date = models.CharField(max_length=10,null=True,blank=True)
    heal_time = models.CharField(max_length=10,null=True,blank=True)
    leave_from_date = models.CharField(max_length=10,null=True,blank=True)
    leave_to_date = models.CharField(max_length=10,null=True,blank=True)
    payment_type = models.CharField(max_length=10,null=True,blank=True)
    join_date = models.CharField(max_length=10,null=True,blank=True)
    accident_place = models.CharField(max_length=10,null=True,blank=True)
    tool_description = models.TextField(null=True,blank=True)
    work_during_acc = models.TextField(null=True,blank=True)

    def __str__(self):
        return str(self.recommender_ssid)


#region Documents
class ClaimDocumentsMaster(models.Model):
    id = models.AutoField(primary_key=True,db_column='DocId')
    DocName = models.CharField(max_length=255,db_column='DocumentName')
    UseBy = models.CharField(max_length=15,db_column='UseBy')#E,A,R1,R2
    EnterDate = models.DateField(db_column='EnterDate')
    Status = models.BooleanField(default=True,db_column='Status')

    def __str__(self):
        return str(self.DocName)

    class Meta:
        managed = True

#endregion

#region HF Bank Details
class HFBankDetails(models.Model):
    bank_id = models.ForeignKey(Bank,on_delete=models.DO_NOTHING,db_column='BankId')
    branch_id = models.ForeignKey(BankBranch,on_delete=models.DO_NOTHING,db_column='BranchId')
    account_name = models.CharField(db_column='AccountName',max_length=60)
    account_number = models.CharField(db_column='AccountNumber',max_length=30)
    health_facility = models.ForeignKey(HealthFacility,on_delete=models.DO_NOTHING,db_column='HF',related_name='bank_details')
    purpose = models.CharField(max_length=15,blank=True,null=True)
    validity_from = models.DateTimeField(db_column='ValidityFrom', blank=True, null=True)
    validity_to = models.DateTimeField(db_column='ValidityTo', blank=True, null=True)
#endregion

