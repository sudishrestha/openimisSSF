from django.contrib import admin
from django.urls import path, include
from .views import *
urlpatterns = [
    path('api-auth/', include('rest_framework.urls')),
    path('gethospitals', APIGetHospitals.as_view()),
    path('getItems', APIGetItems.as_view()),
    path('getServices', APIGetServices.as_view()),
    path('getDiagnosis', APIGetDiagnosis.as_view()),
    path('getClaimRecommend/', APIGetClaimRecommend.as_view()),
    path('gethospitals/<uuid>', APIGetHospitalDetails.as_view()),
    path('getItems/<uuid>', APIGetItemDetails.as_view()),
    path('getServices/<uuid>', APIGetServiceDetails.as_view()),
    path('getDiagnosis/<int:id>', APIGetDiagnosisDetails.as_view()),
    path('getClaimRecommend/<claim_id>', APIGetClaimRecommendDetails.as_view()),
    path('getPatient/<chf_id>', APIGetPatientDetails.as_view()),
    # path('generic/address/<int:AddressId>/', GenericAPIAddressDetails.as_view()),
    # path('generic/address/', GenericAPIAddress.as_view()),
    path('EmployerDetails/<insuree_id>', APIContributorEmpDetails.as_view()),
    path('postClaimOpenImis/', APIPostClaim.as_view()),
    path('documents/<useBy>', GetClaimDocuments.as_view()),
    path('claim/paymentStatus/', PostPaymentStatus.as_view()),
    path('claim/paymentStatus/export', export_payment_report_xls),
    path('claim/invoice/<claimCode>/<invoiceType>', print_invoice),
    # path('generic/contributorEmp/<p_ssid>/', APIContributorEmpDetails.as_view()),
    # path('generic/contributorEmp/', APIContributorEmpList.as_view()),
    # path('generic/Emp/<p_ssid>/', APIEmpDetails.as_view()),
    # path('generic/Emp/', APIEmpList.as_view()),
    # # path('generic/Patient/', InsureeViewSet.as_view({'get': 'list'})),
    # path('generic/bank/', APIListBank.as_view()),
    # path('generic/bank_branch/<int:BankId>', APIListBankBranch.as_view()),
    # path('generic/claim/anusuchi2/',APIClaimAnusuchi2.as_view()),
    # path('generic/claim/anusuchi2/<int:ClaimNo>',APIClaimAnusuchi2.as_view())
]