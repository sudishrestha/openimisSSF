USE [SSF_IMIS_DEMO]
GO
/****** Object:  StoredProcedure [dbo].[uspUpdateClaimFromPhone]    Script Date: 2/24/2022 6:47:54 PM ******/
SET ANSI_NULLS ON
GO
SET QUOTED_IDENTIFIER ON
GO

ALTER PROCEDURE [dbo].[uspUpdateClaimFromPhone]
(
	--@FileName NVARCHAR(255),
	@XML XML,
	@ByPassSubmit BIT = 0
)

/*
-1	-- Fatal Error
0	-- All OK
1	--Invalid HF CODe
2	--Duplicate Claim Code
3	--Invald CHFID
4	--End date is smaller than start date
5	--Invalid ICDCode
6	--Claimed amount is 0
7	--Invalid ItemCode
8	--Invalid ServiceCode
9	--Invalid Claim Admin
*/


AS
BEGIN
	
	SET XACT_ABORT ON

	--DECLARE @XML XML
	
	DECLARE @Query NVARCHAR(3000)

	DECLARE @ClaimID INT
	DECLARE @audit_user_id NVARCHAR(20)
	DECLARE @ClaimDate DATE
	DECLARE @HFCode NVARCHAR(20)
	DECLARE @ClaimAdmin NVARCHAR(8)
	DECLARE @ClaimCode NVARCHAR(60)
	DECLARE @SchemeType NVARCHAR(8)
	DECLARE @subProduct NVARCHAR(8)
	DECLARE @CHFID NVARCHAR(12)
	DECLARE @StartDate DATE
	DECLARE @EndDate DATE
	DECLARE @ICDCode NVARCHAR(6)
	DECLARE @Comment NVARCHAR(MAX)
	DECLARE @Total DECIMAL(18,2)
	DECLARE @ICDCode1 NVARCHAR(6)
	DECLARE @ICDCode2 NVARCHAR(6)
	DECLARE @ICDCode3 NVARCHAR(6)
	DECLARE @ICDCode4 NVARCHAR(6)
	DECLARE @VisitType CHAR(1)
	DECLARE @GuaranteeId NVARCHAR(50)
	
	DECLARE @employer_id NVARCHAR(25)
	DECLARE @is_admitted NVARCHAR(8)
	DECLARE @condition_of_wound NVARCHAR(200)
	DECLARE @injured_body_part NVARCHAR(200)
	DECLARE @is_dead NVARCHAR(8)
	DECLARE @is_disable NVARCHAR(8)
	DECLARE @accident_description NVARCHAR(200)
	DECLARE @reason_of_sickness NVARCHAR(200)
	DECLARE @discharge_type NVARCHAR(50)
	DECLARE @discharge_summary NVARCHAR(200)
	DECLARE @discharge_date DATE

	
	DECLARE @cancer NVARCHAR(8)
	DECLARE @heart_attack NVARCHAR(8)
	DECLARE @high_bp NVARCHAR(8)
	DECLARE @diabetes NVARCHAR(8)
	DECLARE @hiv NVARCHAR(8)


	DECLARE @HFID INT
	DECLARE @ClaimAdminId INT
	DECLARE @InsureeID INT
	DECLARE @ICDID INT
	DECLARE @ICDID1 INT
	DECLARE @ICDID2 INT
	DECLARE @ICDID3 INT
	DECLARE @ICDID4 INT
	DECLARE @TotalItems DECIMAL(18,2) = 0
	DECLARE @TotalServices DECIMAL(18,2) = 0

	DECLARE @isClaimAdminRequired BIT = (SELECT CASE Adjustibility WHEN N'M' THEN 1 ELSE 0 END FROM tblControls WHERE FieldName = N'ClaimAdministrator')
	DECLARE @isClaimAdminOptional BIT = (SELECT CASE Adjustibility WHEN N'O' THEN 1 ELSE 0 END FROM tblControls WHERE FieldName = N'ClaimAdministrator')
	
	BEGIN TRY
		
			IF NOT OBJECT_ID('tempdb..#tblItem') IS NULL DROP TABLE #tblItem
			CREATE TABLE #tblItem(ItemCode NVARCHAR(6),ItemPrice DECIMAL(18,2), ItemQuantity INT)

			IF NOT OBJECT_ID('tempdb..#tblService') IS NULL DROP TABLE #tblService
			CREATE TABLE #tblService(ServiceCode NVARCHAR(6),ServicePrice DECIMAL(18,2), ServiceQuantity INT)

			--SET @Query = (N'SELECT @XML = CAST(X as XML) FROM OPENROWSET(BULK '''+ @FileName +''',SINGLE_BLOB) AS T(X)')
			
			--EXECUTE SP_EXECUTESQL @Query,N'@XML XML OUTPUT',@XML OUTPUT

			SELECT
			@ClaimDate = CONVERT(DATE,Claim.value('(ClaimDate)[1]','NVARCHAR(10)'),103),
			@HFCode = Claim.value('(HFCode)[1]','NVARCHAR(20)'),
			@audit_user_id = Claim.value('(audit_user_id)[1]','NVARCHAR(20)'),
			@ClaimAdmin = Claim.value('(ClaimAdmin)[1]','NVARCHAR(20)'),
			@ClaimCode = Claim.value('(ClaimCode)[1]','NVARCHAR(60)'),
			@SchemeType = Claim.value('(SchemeType)[1]','NVARCHAR(8)'),
			@subProduct = Claim.value('(subProduct)[1]','NVARCHAR(8)'),

			@employer_id = Claim.value('(employer_id)[1]','NVARCHAR(25)'),
			@is_admitted = Claim.value('(is_admitted)[1]','NVARCHAR(8)'),
			@condition_of_wound = Claim.value('(condition_of_wound)[1]','NVARCHAR(200)'),
			@injured_body_part = Claim.value('(injured_body_part)[1]','NVARCHAR(200)'),
			@is_disable = Claim.value('(is_disable)[1]','NVARCHAR(8)'),
			@is_dead = Claim.value('(is_dead)[1]','NVARCHAR(8)'),
			@accident_description = Claim.value('(accident_description)[1]','NVARCHAR(200)'),
			@reason_of_sickness = Claim.value('(reason_of_sickness)[1]','NVARCHAR(200)'),
			@discharge_type = Claim.value('(discharge_type)[1]','NVARCHAR(50)'),
			@discharge_summary = Claim.value('(discharge_summary)[1]','NVARCHAR(200)'),
			@discharge_date = CONVERT(DATE,Claim.value('(discharge_date)[1]','NVARCHAR(10)'),103),

			
			@heart_attack = Claim.value('(heart_attack)[1]','NVARCHAR(8)'),
			@cancer = Claim.value('(cancer)[1]','NVARCHAR(8)'),
			@hiv = Claim.value('(hiv)[1]','NVARCHAR(8)'),
			@diabetes = Claim.value('(diabetes)[1]','NVARCHAR(8)'),
			@high_bp = Claim.value('(high_bp)[1]','NVARCHAR(8)'),

			@CHFID = Claim.value('(CHFID)[1]','NVARCHAR(12)'),
			@StartDate = CONVERT(DATE,Claim.value('(StartDate)[1]','NVARCHAR(10)'),103),
			@EndDate = CONVERT(DATE,Claim.value('(EndDate)[1]','NVARCHAR(10)'),103),
			@ICDCode = Claim.value('(ICDCode)[1]','NVARCHAR(6)'),
			@Comment = Claim.value('(Comment)[1]','NVARCHAR(MAX)'),
			@Total = CASE Claim.value('(Total)[1]','VARCHAR(10)') WHEN '' THEN 0 ELSE CONVERT(DECIMAL(18,2),ISNULL(Claim.value('(Total)[1]','VARCHAR(10)'),0)) END,
			@ICDCode1 = Claim.value('(ICDCode1)[1]','NVARCHAR(6)'),
			@ICDCode2 = Claim.value('(ICDCode2)[1]','NVARCHAR(6)'),
			@ICDCode3 = Claim.value('(ICDCode3)[1]','NVARCHAR(6)'),
			@ICDCode4 = Claim.value('(ICDCode4)[1]','NVARCHAR(6)'),
			@VisitType = Claim.value('(VisitType)[1]','CHAR(1)'),
			@GuaranteeId = Claim.value('(GuaranteeNo)[1]','NVARCHAR(50)')
			FROM @XML.nodes('Claim/Details')AS T(Claim)


			INSERT INTO #tblItem(ItemCode,ItemPrice,ItemQuantity)
			SELECT
			T.Items.value('(ItemCode)[1]','NVARCHAR(6)'),
			CONVERT(DECIMAL(18,2),T.Items.value('(ItemPrice)[1]','DECIMAL(18,2)')),
			CONVERT(DECIMAL(18,2),T.Items.value('(ItemQuantity)[1]','NVARCHAR(15)'))
			FROM @XML.nodes('Claim/Items/Item') AS T(Items)



			INSERT INTO #tblService(ServiceCode,ServicePrice,ServiceQuantity)
			SELECT
			T.[Services].value('(ServiceCode)[1]','NVARCHAR(6)'),
			CONVERT(DECIMAL(18,2),T.[Services].value('(ServicePrice)[1]','DECIMAL(18,2)')),
			CONVERT(DECIMAL(18,2),T.[Services].value('(ServiceQuantity)[1]','NVARCHAR(15)'))
			FROM @XML.nodes('Claim/Services/Service') AS T([Services])

			--isValid HFCode

			SELECT @HFID = HFID FROM tblHF WHERE HFCode = @HFCode AND ValidityTo IS NULL
			IF @HFID IS NULL
				RETURN 1
				
			--isDuplicate ClaimCode
			IF EXISTS(SELECT ClaimCode FROM tblClaim WHERE ClaimCode = @ClaimCode AND HFID = @HFID AND ValidityTo IS NULL)
				RETURN 2

			--isValid CHFID
			SELECT @InsureeID = InsureeID FROM tblInsuree WHERE CHFID = @CHFID AND ValidityTo IS NULL
			IF @InsureeID IS NULL
				RETURN 3

			--isValid EndDate
			IF DATEDIFF(DD,@ENDDATE,@STARTDATE) > 0
				RETURN 4
				
			--isValid ICDCode
			SELECT @ICDID = ICDID FROM tblICDCodes WHERE ICDCode = @ICDCode AND ValidityTo IS NULL
			IF @ICDID IS NULL
				RETURN 5
			
			IF NOT NULLIF(@ICDCode1, '')IS NULL
			BEGIN
				SELECT @ICDID1 = ICDID FROM tblICDCodes WHERE ICDCode = @ICDCode1 AND ValidityTo IS NULL
				IF @ICDID1 IS NULL
					RETURN 5
			END
			
			IF NOT NULLIF(@ICDCode2, '') IS NULL
			BEGIN
				SELECT @ICDID2 = ICDID FROM tblICDCodes WHERE ICDCode = @ICDCode2 AND ValidityTo IS NULL
				IF @ICDID2 IS NULL
					RETURN 5
			END
			
			IF NOT NULLIF(@ICDCode3, '') IS NULL
			BEGIN
				SELECT @ICDID3 = ICDID FROM tblICDCodes WHERE ICDCode = @ICDCode3 AND ValidityTo IS NULL
				IF @ICDID3 IS NULL
					RETURN 5
			END
			
			IF NOT NULLIF(@ICDCode4, '') IS NULL
			BEGIN
				SELECT @ICDID4 = ICDID FROM tblICDCodes WHERE ICDCode = @ICDCode4 AND ValidityTo IS NULL
				IF @ICDID4 IS NULL
					RETURN 5
			END		
			--isValid Claimed Amount
			--THIS CONDITION CAN BE PUT BACK
			--IF @Total <= 0
			--	RETURN 6
				
			--isValid ItemCode
			IF EXISTS (SELECT I.ItemCode
			FROM tblItems I FULL OUTER JOIN #tblItem TI ON I.ItemCode COLLATE DATABASE_DEFAULT = TI.ItemCode COLLATE DATABASE_DEFAULT
			WHERE I.ItemCode IS NULL AND I.ValidityTo IS NULL)
				RETURN 7
				
			--isValid ServiceCode
			IF EXISTS(SELECT S.ServCode
			FROM tblServices S FULL OUTER JOIN #tblService TS ON S.ServCode COLLATE DATABASE_DEFAULT = TS.ServiceCode COLLATE DATABASE_DEFAULT
			WHERE S.ServCode IS NULL AND S.ValidityTo IS NULL)
				RETURN 8
			
			--isValid Claim Admin
			IF @isClaimAdminRequired = 1
				BEGIN	
					SELECT @ClaimAdminId = ClaimAdminId FROM tblClaimAdmin WHERE ClaimAdminCode = @ClaimAdmin AND ValidityTo IS NULL
					IF @ClaimAdmin IS NULL
						RETURN 9
				END
			ELSE
				IF @isClaimAdminOptional = 1
					BEGIN	
						SELECT @ClaimAdminId = ClaimAdminId FROM tblClaimAdmin WHERE ClaimAdminCode = @ClaimAdmin AND ValidityTo IS NULL
					END

		BEGIN TRAN CLAIM
			INSERT INTO tblClaim(InsureeID,ClaimCode,DateFrom,DateTo,ICDID,ClaimStatus,Claimed,DateClaimed,Explanation,AuditUserID,HFID,ClaimAdminId,ICDID1,ICDID2,ICDID3,ICDID4,VisitType,GuaranteeId,product_id,subProduct_id,IsAdmitted,ConditionOfWound,InjuredBodyPart,is_disable,IsDead,AccidentDescription,ReasonOfSickness,DischargeType,DischargeSummary,ReferToDate,Cancer,HIV,HighBp,Diabetes,HeartAttack,employer_id)
						VALUES(@InsureeID,@ClaimCode,@StartDate,@EndDate,@ICDID,2,@Total,@ClaimDate,@Comment,@audit_user_id,@HFID,@ClaimAdminId,@ICDID1,@ICDID2,@ICDID3,@ICDID4,@VisitType,@GuaranteeId,@SchemeType,@subProduct,@is_admitted,@condition_of_wound,@injured_body_part,@is_disable,@is_dead,@accident_description,@reason_of_sickness,@discharge_type,@discharge_summary,@discharge_date,@cancer,@hiv,@high_bp,@diabetes,@heart_attack,@employer_id);

			SELECT @ClaimID = SCOPE_IDENTITY();
			
			;WITH PLID AS
			(
				SELECT PLID.ItemId, PLID.PriceOverule
				FROM tblHF HF
				INNER JOIN tblPLItems PLI ON PLI.PLItemId = HF.PLItemID
				INNER JOIN tblPLItemsDetail PLID ON PLID.PLItemId = PLI.PLItemId
				WHERE HF.ValidityTo IS NULL
				AND PLI.ValidityTo IS NULL
				AND PLID.ValidityTo IS NULL
				AND HF.HFID = @HFID
			)
			--- Update tblClaim set AuditUserIDSubmit = @audit_user_id where ClaimID= @ClaimID;
			INSERT INTO tblClaimItems(ClaimID,ItemID,QtyProvided,PriceAsked,AuditUserID)
			SELECT @ClaimID, I.ItemId, T.ItemQuantity, COALESCE(NULLIF(T.ItemPrice,0),PLID.PriceOverule,I.ItemPrice)ItemPrice, -1
			FROM #tblItem T 
			INNER JOIN tblItems I  ON T.ItemCode COLLATE DATABASE_DEFAULT = I.ItemCode COLLATE DATABASE_DEFAULT AND I.ValidityTo IS NULL
			LEFT OUTER JOIN PLID ON PLID.ItemID = I.ItemID
			
			SELECT @TotalItems = SUM(PriceAsked * QtyProvided) FROM tblClaimItems 
						WHERE ClaimID = @ClaimID
						GROUP BY ClaimID

			;WITH PLSD AS
			(
				SELECT PLSD.ServiceId, PLSD.PriceOverule
				FROM tblHF HF
				INNER JOIN tblPLServices PLS ON PLS.PLServiceId = HF.PLServiceID
				INNER JOIN tblPLServicesDetail PLSD ON PLSD.PLServiceId = PLS.PLServiceId
				WHERE HF.ValidityTo IS NULL
				AND PLS.ValidityTo IS NULL
				AND PLSD.ValidityTo IS NULL
				AND HF.HFID = @HFID
			)
			INSERT INTO tblClaimServices(ClaimId, ServiceID, QtyProvided, PriceAsked, AuditUserID)
			SELECT @ClaimID, S.ServiceID, T.ServiceQuantity,COALESCE(NULLIF(T.ServicePrice,0),PLSD.PriceOverule,S.ServPrice)ServicePrice , -1
			FROM #tblService T 
			INNER JOIN tblServices S ON T.ServiceCode COLLATE DATABASE_DEFAULT = S.ServCode COLLATE DATABASE_DEFAULT AND S.ValidityTo IS NULL
			LEFT OUTER JOIN PLSD ON PLSD.ServiceId = S.ServiceId
						
						SELECT @TotalServices = SUM(PriceAsked * QtyProvided) FROM tblClaimServices 
						WHERE ClaimID = @ClaimID
						GROUP BY ClaimID
					
						UPDATE tblClaim SET Claimed = ISNULL(@TotalItems,0) + ISNULL(@TotalServices,0)
						WHERE ClaimID = @ClaimID
						
		COMMIT TRAN CLAIM
		
		
		SELECT @ClaimID  = IDENT_CURRENT('tblClaim')
		
		IF @ByPassSubmit = 0
			EXEC uspSubmitSingleClaim @audit_user_id, @ClaimID,0 
		
	END TRY
	BEGIN CATCH
		IF @@TRANCOUNT > 0
			ROLLBACK TRAN CLAIM
			SELECT ERROR_MESSAGE()
		RETURN -1
	END CATCH
	
	RETURN 0
END
