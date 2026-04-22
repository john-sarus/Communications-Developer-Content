public with sharing class ATCCalculateTaxInvocable {
    @TestVisible private static final String NAMED_CREDENTIAL = 'ATC_Adapter_Static';
    @TestVisible private static final Decimal DEFAULT_LINE_AMOUNT = 1;
    @TestVisible private static final Integer DEFAULT_PCODE = 4100;

    public class Request {
        @InvocableVariable(required=true)
        public Id recordId;

        @InvocableVariable
        public String sourceObject;

        @InvocableVariable
        public Decimal lineAmount;

        @InvocableVariable
        public Integer pCode;

        @InvocableVariable
        public Integer transactionType;

        @InvocableVariable
        public Integer serviceType;

        @InvocableVariable
        public String customerType;
    }

    public class Result {
        @InvocableVariable
        public Id recordId;

        @InvocableVariable
        public String sourceObject;

        @InvocableVariable
        public Boolean success;

        @InvocableVariable
        public String status;

        @InvocableVariable
        public Decimal totalTaxAmount;

        @InvocableVariable
        public String message;

        @InvocableVariable
        public String requestPayload;

        @InvocableVariable
        public String responsePayload;
    }

    @InvocableMethod(
        label='Calculate ATC Tax'
        description='Calls the ATC adapter for Contract and Order records.'
    )
    public static List<Result> calculate(List<Request> requests) {
        List<Result> results = new List<Result>();
        for (Request requestItem : requests) {
            results.add(processRequest(requestItem));
        }
        return results;
    }

    private static Result processRequest(Request requestItem) {
        Result result = new Result();
        result.recordId = requestItem.recordId;

        String sourceObject = normalizeSourceObject(requestItem);
        result.sourceObject = sourceObject;

        try {
            SObject recordItem = loadRecord(requestItem.recordId, sourceObject);
            Integer transactionType = resolveTypeCode(
                requestItem.transactionType,
                recordItem,
                'ATC_Transaction_Type__c'
            );
            Integer serviceType = resolveTypeCode(
                requestItem.serviceType,
                recordItem,
                'ATC_Service_Type__c'
            );

            if (transactionType == null || serviceType == null) {
                throw new ATCException('ATC Transaction Type and ATC Service Type are required.');
            }

            String requestPayload = buildRequestPayload(
                recordItem,
                sourceObject,
                requestItem,
                transactionType,
                serviceType
            );
            result.requestPayload = requestPayload;

            HttpRequest httpRequest = new HttpRequest();
            httpRequest.setEndpoint('callout:' + NAMED_CREDENTIAL + buildPath(sourceObject));
            httpRequest.setMethod('POST');
            httpRequest.setHeader('Content-Type', 'application/json');
            httpRequest.setHeader('Idempotency-Key', buildIdempotencyKey(recordItem, sourceObject));
            httpRequest.setHeader('X-Correlation-Id', buildCorrelationId(recordItem));
            httpRequest.setTimeout(10000);
            httpRequest.setBody(requestPayload);

            HttpResponse response = new Http().send(httpRequest);
            String responsePayload = response.getBody();
            result.responsePayload = responsePayload;
            String afcRequestPayload = extractStringField(responsePayload, 'afc_request_payload');
            String afcResponsePayload = extractStringField(responsePayload, 'afc_response_payload');

            if (response.getStatusCode() >= 200 && response.getStatusCode() < 300) {
                Decimal totalTaxAmount = extractTotalTaxAmount(responsePayload);
                updateRecordState(
                    recordItem,
                    'Calculated',
                    totalTaxAmount,
                    requestPayload,
                    responsePayload,
                    afcRequestPayload,
                    afcResponsePayload
                );
                if (sourceObject == 'Order') {
                    upsertOrderItemTaxLines(recordItem.Id, responsePayload);
                }
                result.success = true;
                result.status = 'Calculated';
                result.totalTaxAmount = totalTaxAmount;
                result.message = 'ATC tax calculated.';
                return result;
            }

            updateRecordState(
                recordItem,
                'Error',
                null,
                requestPayload,
                responsePayload,
                afcRequestPayload,
                afcResponsePayload
            );
            result.success = false;
            result.status = 'Error';
            result.message = 'ATC adapter call failed with status code ' + response.getStatusCode() + '.';
            return result;
        } catch (Exception ex) {
            String errorPayload = buildErrorPayload(ex.getMessage());
            safeWriteError(requestItem.recordId, sourceObject, result.requestPayload, errorPayload);
            result.success = false;
            result.status = 'Error';
            result.responsePayload = errorPayload;
            result.message = ex.getMessage();
            return result;
        }
    }

    private static String normalizeSourceObject(Request requestItem) {
        if (String.isNotBlank(requestItem.sourceObject)) {
            if (requestItem.sourceObject == 'Contract' || requestItem.sourceObject == 'Order') {
                return requestItem.sourceObject;
            }
            throw new ATCException('Unsupported source object: ' + requestItem.sourceObject + '.');
        }

        String derivedName = String.valueOf(requestItem.recordId.getSObjectType());
        if (derivedName == 'Contract' || derivedName == 'Order') {
            return derivedName;
        }
        throw new ATCException('Only Contract and Order records are supported.');
    }

    private static SObject loadRecord(Id recordId, String sourceObject) {
        Map<String, Schema.SObjectField> fieldsMap =
            Schema.getGlobalDescribe().get(sourceObject).getDescribe().fields.getMap();

        List<String> selectedFields = new List<String>{
            'Id',
            'AccountId',
            'LastModifiedDate',
            'ATC_Calc_Status__c',
            'ATC_Transaction_Type__c',
            'ATC_Service_Type__c',
            'ATC_Estimated_Tax_Amount__c',
            'ATC_Last_Calculated_At__c',
            'ATC_Last_Request_Payload__c',
            'ATC_Last_Response_Payload__c',
            'ATC_AFC_Request_Payload__c',
            'ATC_AFC_Response_Payload__c'
        };

        addFieldIfPresent(fieldsMap, selectedFields, 'CurrencyIsoCode');
        addFieldIfPresent(fieldsMap, selectedFields, 'ContractNumber');
        addFieldIfPresent(fieldsMap, selectedFields, 'OrderNumber');
        addFieldIfPresent(fieldsMap, selectedFields, 'StartDate');
        addFieldIfPresent(fieldsMap, selectedFields, 'EffectiveDate');
        addFieldIfPresent(fieldsMap, selectedFields, 'TotalAmount');

        String queryText =
            'SELECT ' + String.join(selectedFields, ', ') +
            ' FROM ' + sourceObject +
            ' WHERE Id = :recordId LIMIT 1';
        return Database.query(queryText);
    }

    private static void addFieldIfPresent(
        Map<String, Schema.SObjectField> fieldsMap,
        List<String> selectedFields,
        String fieldName
    ) {
        if (fieldsMap.containsKey(fieldName)) {
            selectedFields.add(fieldName);
        }
    }

    private static Integer resolveTypeCode(Integer requestValue, SObject recordItem, String fieldName) {
        if (requestValue != null) {
            return requestValue;
        }
        if (recordItem.get(fieldName) == null) {
            return null;
        }
        return Integer.valueOf(String.valueOf(recordItem.get(fieldName)));
    }

    private static String buildRequestPayload(
        SObject recordItem,
        String sourceObject,
        Request requestItem,
        Integer transactionType,
        Integer serviceType
    ) {
        String documentCode = resolveDocumentCode(recordItem, sourceObject);
        String documentDate = resolveDocumentDate(recordItem, sourceObject);
        String currencyCode = resolveCurrency(recordItem);
        Object accountIdValue = recordItem.get('AccountId');
        if (accountIdValue == null) {
            throw new ATCException('AccountId is required.');
        }
        String accountId = String.valueOf(accountIdValue);

        Integer pCode = requestItem.pCode == null ? DEFAULT_PCODE : requestItem.pCode;
        String productCode = 'ATC-TS-' + String.valueOf(transactionType) + '-' + String.valueOf(serviceType);
        Map<String, Object> locationPCode = new Map<String, Object>{ 'pcd' => pCode };

        List<Object> lines;
        if (sourceObject == 'Order') {
            lines = buildOrderLines(recordItem.Id, requestItem, productCode, locationPCode, transactionType, serviceType);
        } else {
            Decimal amount = resolveLineAmount(recordItem, requestItem);
            String lineId = sourceObject.toLowerCase() + '-' + String.valueOf(recordItem.get('Id'));
            lines = new List<Object>{
                new Map<String, Object>{
                    'line_id' => lineId,
                    'product_code' => productCode,
                    'amount' => amount,
                    'quantity' => 1,
                    'from_address' => locationPCode,
                    'to_address' => locationPCode,
                    'bill_to_address' => locationPCode
                }
            };
        }

        Map<String, Object> payload = new Map<String, Object>{
            'source_object' => sourceObject,
            'salesforce_record_id' => String.valueOf(recordItem.get('Id')),
            'document_code' => documentCode,
            'document_date' => documentDate,
            'account_id' => accountId,
            'account_name' => null,
            'customer_type' => String.isBlank(requestItem.customerType) ? 'Business' : requestItem.customerType,
            'currency_iso_code' => currencyCode,
            'transaction_type' => transactionType,
            'service_type' => serviceType,
            'lines' => lines
        };

        return JSON.serialize(payload);
    }

    private static List<Object> buildOrderLines(
        Id orderId,
        Request requestItem,
        String productCode,
        Map<String, Object> locationPCode,
        Integer transactionType,
        Integer serviceType
    ) {
        List<OrderItem> orderItems = [
            SELECT Id, LineNumber, Quantity, TotalPrice, UnitPrice
            FROM OrderItem
            WHERE OrderId = :orderId
            ORDER BY LineNumber ASC
        ];

        List<Object> lines = new List<Object>();
        for (OrderItem item : orderItems) {
            Integer lineNum = item.LineNumber == null ? 1 : Integer.valueOf(item.LineNumber);
            Decimal amount = item.TotalPrice != null ? item.TotalPrice.setScale(2) : (item.UnitPrice != null ? (item.UnitPrice * item.Quantity).setScale(2) : DEFAULT_LINE_AMOUNT);
            lines.add(new Map<String, Object>{
                'line_id'          => 'line-' + lineNum,
                'product_code'     => productCode,
                'amount'           => amount,
                'quantity'         => item.Quantity != null ? item.Quantity : 1,
                'from_address'     => locationPCode,
                'to_address'       => locationPCode,
                'bill_to_address'  => locationPCode
            });
        }

        // Fall back to a single order-level line if no OrderItems exist yet
        if (lines.isEmpty()) {
            Decimal amount = requestItem.lineAmount != null ? requestItem.lineAmount.setScale(2) : DEFAULT_LINE_AMOUNT;
            lines.add(new Map<String, Object>{
                'line_id'         => 'line-1',
                'product_code'    => productCode,
                'amount'          => amount,
                'quantity'        => 1,
                'from_address'    => locationPCode,
                'to_address'      => locationPCode,
                'bill_to_address' => locationPCode
            });
        }
        return lines;
    }

    private static String resolveDocumentCode(SObject recordItem, String sourceObject) {
        Object contractNumber = getValueIfPresent(recordItem, 'ContractNumber');
        if (sourceObject == 'Contract' && contractNumber != null) {
            return String.valueOf(contractNumber);
        }
        Object orderNumber = getValueIfPresent(recordItem, 'OrderNumber');
        if (sourceObject == 'Order' && orderNumber != null) {
            return String.valueOf(orderNumber);
        }
        return String.valueOf(recordItem.get('Id'));
    }

    private static String resolveDocumentDate(SObject recordItem, String sourceObject) {
        Date sourceDate;
        Object startDate = getValueIfPresent(recordItem, 'StartDate');
        Object effectiveDate = getValueIfPresent(recordItem, 'EffectiveDate');
        if (sourceObject == 'Contract' && startDate != null) {
            sourceDate = (Date) startDate;
        } else if (sourceObject == 'Order' && effectiveDate != null) {
            sourceDate = (Date) effectiveDate;
        } else {
            sourceDate = Date.today();
        }

        Datetime dt = Datetime.newInstance(sourceDate, Time.newInstance(0, 0, 0, 0));
        return dt.formatGmt('yyyy-MM-dd') + 'T' + dt.formatGmt('HH:mm:ss') + 'Z';
    }

    private static String resolveCurrency(SObject recordItem) {
        Object value = getValueIfPresent(recordItem, 'CurrencyIsoCode');
        if (value == null) {
            return 'USD';
        }
        return String.valueOf(value);
    }

    private static Decimal resolveLineAmount(SObject recordItem, Request requestItem) {
        if (requestItem.lineAmount != null) {
            return requestItem.lineAmount.setScale(2);
        }
        Object totalAmount = getValueIfPresent(recordItem, 'TotalAmount');
        if (totalAmount != null) {
            return ((Decimal) totalAmount).setScale(2);
        }
        return DEFAULT_LINE_AMOUNT.setScale(2);
    }

    private static String buildPath(String sourceObject) {
        return sourceObject == 'Contract'
            ? '/v1/tax/contract/calculate'
            : '/v1/tax/order/calculate';
    }

    private static String buildIdempotencyKey(SObject recordItem, String sourceObject) {
        Datetime lastModified = (Datetime) recordItem.get('LastModifiedDate');
        Long marker = lastModified == null ? Datetime.now().getTime() : lastModified.getTime();
        return sourceObject.toLowerCase() + '-' + String.valueOf(recordItem.get('Id')) + '-' + String.valueOf(marker);
    }

    private static String buildCorrelationId(SObject recordItem) {
        return String.valueOf(recordItem.get('Id')) + '-' + String.valueOf(Datetime.now().getTime());
    }

    private static Decimal extractTotalTaxAmount(String responsePayload) {
        if (String.isBlank(responsePayload)) {
            return 0;
        }

        Map<String, Object> parsed = (Map<String, Object>) JSON.deserializeUntyped(responsePayload);
        Object rawValue = parsed.get('total_tax_amount');
        if (rawValue == null) {
            return 0;
        }
        return Decimal.valueOf(String.valueOf(rawValue)).setScale(2);
    }

    private static void updateRecordState(
        SObject recordItem,
        String calcStatus,
        Decimal totalTaxAmount,
        String requestPayload,
        String responsePayload,
        String afcRequestPayload,
        String afcResponsePayload
    ) {
        recordItem.put('ATC_Calc_Status__c', calcStatus);
        recordItem.put('ATC_Last_Request_Payload__c', requestPayload);
        recordItem.put('ATC_Last_Response_Payload__c', responsePayload);
        recordItem.put('ATC_AFC_Request_Payload__c', afcRequestPayload);
        recordItem.put('ATC_AFC_Response_Payload__c', afcResponsePayload);
        recordItem.put('ATC_Last_Calculated_At__c', System.now());
        if (totalTaxAmount != null) {
            recordItem.put('ATC_Estimated_Tax_Amount__c', totalTaxAmount);
        }
        update recordItem;
    }

    private static void safeWriteError(
        Id recordId,
        String sourceObject,
        String requestPayload,
        String responsePayload
    ) {
        try {
            SObject recordItem = loadRecord(recordId, sourceObject);
            updateRecordState(
                recordItem,
                'Error',
                null,
                requestPayload,
                responsePayload,
                extractStringField(responsePayload, 'afc_request_payload'),
                extractStringField(responsePayload, 'afc_response_payload')
            );
        } catch (Exception ignoreError) {
        }
    }

    private static String buildErrorPayload(String message) {
        return JSON.serialize(new Map<String, Object>{
            'status' => 'error',
            'error' => new Map<String, Object>{
                'message' => message
            }
        });
    }

    private static Object getValueIfPresent(SObject recordItem, String fieldName) {
        Map<String, Object> populatedFields = recordItem.getPopulatedFieldsAsMap();
        if (populatedFields.containsKey(fieldName)) {
            return populatedFields.get(fieldName);
        }
        return null;
    }

    private static String extractStringField(String payload, String fieldName) {
        if (String.isBlank(payload)) {
            return null;
        }

        try {
            Map<String, Object> parsed = (Map<String, Object>) JSON.deserializeUntyped(payload);
            Object rawValue = parsed.get(fieldName);
            return rawValue == null ? null : String.valueOf(rawValue);
        } catch (Exception ignoreError) {
            return null;
        }
    }

    private static void upsertOrderItemTaxLines(Id orderId, String responsePayload) {
        List<ATC_Tax_Line__c> existing = [
            SELECT Id FROM ATC_Tax_Line__c WHERE Order__c = :orderId
        ];
        if (!existing.isEmpty()) {
            delete existing;
        }

        Map<String, Object> parsed = (Map<String, Object>) JSON.deserializeUntyped(responsePayload);
        List<Object> lines = (List<Object>) parsed.get('lines');
        if (lines == null || lines.isEmpty()) {
            return;
        }

        List<ATC_Tax_Line__c> newTaxLines = new List<ATC_Tax_Line__c>();
        for (Object lineObj : lines) {
            Map<String, Object> line = (Map<String, Object>) lineObj;
            String lineId = line.get('line_id') != null ? String.valueOf(line.get('line_id')) : '';
            Integer lineNumber = parseLineNumber(lineId);

            List<Object> components = (List<Object>) line.get('components');
            if (components == null || components.isEmpty()) {
                continue;
            }

            for (Object comp : components) {
                Map<String, Object> component = (Map<String, Object>) comp;
                Integer level = Integer.valueOf(String.valueOf(component.get('level')));
                Integer taxTypeId = Integer.valueOf(String.valueOf(component.get('tax_type_id')));
                Decimal rate = Decimal.valueOf(String.valueOf(component.get('rate')));
                Decimal taxAmount = Decimal.valueOf(String.valueOf(component.get('tax')));
                String levelName = taxLevelName(level);
                String taxName = component.get('name') != null ? String.valueOf(component.get('name')) : '';
                String taxCategory = component.get('category') != null ? String.valueOf(component.get('category')) : '';
                Integer jurisdictionPcode = component.get('jurisdiction_pcode') != null
                    ? Integer.valueOf(String.valueOf(component.get('jurisdiction_pcode'))) : 0;

                ATC_Tax_Line__c taxLine = new ATC_Tax_Line__c();
                taxLine.Name = String.isNotBlank(taxName) ? taxName.abbreviate(80) : 'AFC Tax - ' + levelName;
                taxLine.Order__c = orderId;
                taxLine.Order_Line_Number__c = lineNumber;
                taxLine.Amount__c = taxAmount.setScale(2, RoundingMode.HALF_UP);
                taxLine.Rate__c = (rate * 100).setScale(4, RoundingMode.HALF_UP);
                taxLine.Tax_Level__c = levelName;
                taxLine.Tax_Type_Id__c = taxTypeId;
                taxLine.Tax_Name__c = taxName;
                taxLine.Tax_Category__c = taxCategory;
                taxLine.Jurisdiction_PCode__c = jurisdictionPcode > 0 ? jurisdictionPcode : null;
                taxLine.Jurisdiction_State__c = component.get('jurisdiction_state') != null
                    ? String.valueOf(component.get('jurisdiction_state')) : '';
                taxLine.Jurisdiction_County__c = component.get('jurisdiction_county') != null
                    ? String.valueOf(component.get('jurisdiction_county')) : '';
                taxLine.Jurisdiction_City__c = component.get('jurisdiction_city') != null
                    ? String.valueOf(component.get('jurisdiction_city')) : '';
                taxLine.Billable__c = component.get('billable') != null
                    ? Boolean.valueOf(String.valueOf(component.get('billable'))) : false;
                taxLine.Compliant__c = component.get('compliant') != null
                    ? Boolean.valueOf(String.valueOf(component.get('compliant'))) : false;
                taxLine.Surcharge__c = component.get('surcharge') != null
                    ? Boolean.valueOf(String.valueOf(component.get('surcharge'))) : false;
                taxLine.Taxable_Measure__c = component.get('taxable_measure') != null
                    ? Decimal.valueOf(String.valueOf(component.get('taxable_measure'))).setScale(4, RoundingMode.HALF_UP) : 0;
                taxLine.Exempt_Amount__c = component.get('exempt_amount') != null
                    ? Decimal.valueOf(String.valueOf(component.get('exempt_amount'))).setScale(2, RoundingMode.HALF_UP) : 0;
                taxLine.Calc_Type__c = component.get('calc_type') != null
                    ? Integer.valueOf(String.valueOf(component.get('calc_type'))) : null;
                taxLine.Category_Id__c = component.get('category_id') != null
                    ? Integer.valueOf(String.valueOf(component.get('category_id'))) : null;
                taxLine.Lines__c = component.get('lines') != null
                    ? Integer.valueOf(String.valueOf(component.get('lines'))) : null;
                taxLine.Minutes__c = component.get('minutes') != null
                    ? Decimal.valueOf(String.valueOf(component.get('minutes'))) : null;
                newTaxLines.add(taxLine);
            }
        }

        if (!newTaxLines.isEmpty()) {
            insert newTaxLines;
        }
    }

    // Extracts the integer from a line_id like "line-1" or "line-12"
    private static Integer parseLineNumber(String lineId) {
        if (String.isBlank(lineId)) {
            return null;
        }
        Integer dashIdx = lineId.lastIndexOf('-');
        if (dashIdx == -1 || dashIdx == lineId.length() - 1) {
            return null;
        }
        String numStr = lineId.substring(dashIdx + 1);
        try {
            return Integer.valueOf(numStr);
        } catch (Exception e) {
            return null;
        }
    }

    private static String taxLevelName(Integer level) {
        if (level == 0) return 'Federal';
        if (level == 1) return 'State';
        if (level == 2) return 'County';
        if (level == 3) return 'City';
        return 'Other';
    }

    public class ATCException extends Exception {
    }
}
