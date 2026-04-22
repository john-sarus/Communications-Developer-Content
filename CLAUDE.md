# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

Avalara Communications Developer Content — API documentation, sample code, and auto-generated SDKs for Avalara's Communications tax services. Three main product areas:

- **afc_saaspro_tax/** — SaaS Pro Tax REST and SOAP APIs, SDKs, manuals, and tax reference docs
- **afc_saaspro_geo/** — SaaS Pro Geo geocoding/jurisdiction APIs with language-specific samples
- **afc_saasstd_tax/** — SaaS Standard Tax sample configurations and documentation

## SDKs

All SDKs live under `afc_saaspro_tax/afc_rest_apis/SDK/` and are **generated via openapi-generator** from OpenAPI specs. Five language SDKs:

| Language | Path | Build | Test |
|----------|------|-------|------|
| C# .NET Core | `SDK/csharp-netcore/` | `dotnet build` | AppVeyor CI |
| Java | `SDK/java/` | `mvn compile` or `./gradlew build` | `mvn test` |
| JavaScript | `SDK/javascript/` | `npm install` | `npm test` (Mocha) |
| PHP | `SDK/php/` | `composer install` | `./vendor/bin/phpunit` |
| Python | `SDK/python/` | `python setup.py install` | `tox` |

## API Reference — AvaTax Communications REST v2

Base URL: `https://communications.avalara.net` (production) / `https://communicationsua.avalara.net` (UAT)

### Authentication

- **Basic Auth** (required): HTTP Basic with username/password credentials
- **`client_id`** header (required): Integer client ID, must be sent on every request
- **`client_profile_id`** header (optional): Integer profile number for taxation profile selection
- **TLS 1.2+** required on all connections

### Endpoints

| Method | Path | Tag | Summary | Request | Response |
|--------|------|-----|---------|---------|----------|
| POST | `/api/v2/afc/calcTaxes` | Tax Calculation | Calculate taxes on invoices/line items | CalcTaxesRequest | CalcTaxesResponse |
| POST | `/api/v2/afc/commit` | Tax Calculation | Commit or un-commit a document code | CommitRequest | CommitResponse |
| POST | `/api/v2/afc/pCode` | Jurisdiction | Look up PCode(s) by location | PCodeLookupRequest | PCodeLookupResult |
| POST | `/api/v2/geo/geocode` | Jurisdiction | Geocode street addresses and/or lat/long | GeocodeRequest[] | GeocodeResult[] |
| POST | `/api/v2/geo/batch/upload` | Jurisdiction | Upload file for batch geocoding | multipart file | GeoBatchSubmitFileResponse |
| GET | `/api/v2/geo/batch/status/{processId}` | Jurisdiction | Get batch geocode file status | — | GeoBatchStatus |
| GET | `/api/v2/geo/batch/log/{processId}` | Jurisdiction | Get batch geocode file log | — | GeoBatchLog |
| GET | `/api/v2/afc/taxType/{taxType}` | Lookups | Get tax type description/category (`*` = all) | — | TaxTypeData[] |
| GET | `/api/v2/afc/tsPairs` | Lookups | Get transaction/service pair info | — | TsPairData[] |
| GET | `/api/v2/afc/location/{pCode}` | Lookups | Get location data for a PCode | — | PCodeLookupResult |
| GET | `/api/v2/afc/primary/{pCode}` | Lookups | Get primary location for a PCode | — | PCodeLookupResult |
| GET | `/api/v2/afc/serviceInfo` | Lookups | Server time & version info (deprecated, use /api/health) | — | ServiceInfo |
| GET | `/api/v2/BundlePackages` | Customizations | List bundle packages (paged, filterable) | — | BundlePackageDtoPagedList |
| GET | `/api/v2/BundlePackages/{id}` | Customizations | Get bundle package by ID | — | BundlePackageDto |
| GET | `/api/v2/BundlePackages/{id}/export` | Customizations | Export bundle package | — | file |
| GET | `/api/v2/ExclusionCollections` | Customizations | List exclusion collections | — | ExclusionCollectionDtoPagedList |
| GET | `/api/v2/ExclusionCollections/{id}` | Customizations | Get exclusion collection by ID | — | ExclusionCollectionDto |
| GET | `/api/v2/ExclusionCollections/{id}/export` | Customizations | Export exclusion collection | — | file |
| GET | `/api/v2/OverrideGroups` | Customizations | List override group summaries | — | OverrideGroupSummaryDtoPagedList |
| GET | `/api/v2/OverrideGroups/{id}` | Customizations | Get override group by ID | — | OverrideGroupDto |
| GET | `/api/v2/OverrideGroups/{id}/export` | Customizations | Export override group | — | file |
| GET | `/api/v2/OverrideGroups/{id}/engineExport` | Customizations | Engine-formatted override group | — | string[] |
| GET | `/api/v2/Profiles` | Customizations | List profiles | — | ProfileDtoPagedList |
| GET | `/api/v2/Profiles/{id}` | Customizations | Get profile by ID | — | ProfileDto |
| GET | `/api/v2/SafeHarborOverrideSettings` | Customizations | List safe harbor override settings | — | SafeHarborOverrideSettingsDtoPagedList |
| GET | `/api/v2/SafeHarborOverrideSettings/{id}` | Customizations | Get safe harbor override by ID | — | SafeHarborOverrideSettingsDto |
| GET | `/api/v2/SafeHarborOverrideSettings/{id}/export` | Customizations | Export safe harbor override | — | file |
| GET | `/api/v2/TaxCalculationSettings` | Customizations | List tax calculation settings | — | TaxCalculationSettingsDtoPagedList |
| GET | `/api/v2/TaxCalculationSettings/{id}` | Customizations | Get tax calculation settings by ID | — | TaxCalculationSettingsDto |

All Customization list endpoints support OData-style query params: `Filter`, `OrderBy`, `Skip`, `Top`, `Count`, `CountOnly`.

### Key Object Schemas

#### CalcTaxesRequest
| Property | Type | Description |
|----------|------|-------------|
| `cfg` | RequestConfig | Request configuration options |
| `cmpn` | CompanyData | Company data |
| `inv` | Invoice[] | Invoices to process |
| `ovr` | TaxOverride[] | Tax rate overrides |
| `sovr` | SafeHarborOverride[] | Safe harbor overrides for USF taxes |

#### CompanyData
| Property | Type | Description |
|----------|------|-------------|
| `bscl` | int16 | Business class: 0=ILEC, 1=CLEC |
| `svcl` | int16 | Service class: 0=Primary Local, 1=Primary Long Distance |
| `fclt` | bool | Company owns facilities to provide service |
| `frch` | bool | Services sold under franchise agreement |
| `reg` | bool | Company is regulated |
| `excl` | Exclusion[] | State exclusion list |
| `idnt` | string | Optional company identifier for reporting |

#### Invoice
| Property | Type | Description |
|----------|------|-------------|
| `doc` | string | Document code |
| `cmmt` | bool | Commit on process (default: false) |
| `bill` | Location | Billing location |
| `cust` | int16 | Customer type (see enum below) |
| `lfln` | bool | Lifeline participant (default: false) |
| `date` | datetime | Invoice date |
| `exms` | TaxExemption[] | Tax exemptions |
| `itms` | LineItem[] | Line items |
| `invm` | bool | Invoice mode — all items taxed together (default: true) |
| `dtl` | bool | Return individual line item taxes (default: true) |
| `summ` | bool | Return summarized invoice taxes (default: false) |
| `opt` | KeyValuePair[] | Optional reporting values (max 5, keys 1-5) |
| `acct` | string | Account reference |
| `custref` | string | Customer reference |
| `invn` | string | Invoice number reference |
| `bcyc` | string | Bill cycle reference |
| `bpd` | BillingPeriod | Billing period (month + year) |
| `ccycd` | string | Currency code (e.g. "CAD") |

#### LineItem
| Property | Type | Description |
|----------|------|-------------|
| `ref` | string | Reference ID |
| `from` | Location | Origination location |
| `to` | Location | Termination location |
| `chg` | double | Charge amount (default: 0) |
| `line` | int32 | Number of lines (default: 0) |
| `loc` | int32 | Number of locations (default: 0) |
| `min` | double | Number of minutes (default: 0) |
| `sale` | int16 | Sale type (see enum below) |
| `plsp` | double | Private line split percentage |
| `incl` | bool | Tax inclusive (default: false) |
| `pror` | double | Pro-rated percentage |
| `proadj` | int32 | Pro-rated adjustment: 0=none, 1=exclude non-proratable fixed, 2=include |
| `tran` | int16 | Transaction type ID |
| `serv` | int16 | Service type ID |
| `dbt` | bool | Prepaid/debit (default: false) |
| `adj` | bool | Is adjustment (default: false) |
| `disc` | int16 | Discount type (see enum below) |
| `prop` | int16 | Sales and Use attribute property |
| `bill` | Location | Line-level billing location override |
| `cust` | int16 | Line-level customer type override |
| `lfln` | bool | Line-level Lifeline override |
| `date` | datetime | Line-level invoice date override |
| `qty` | int16 | Quantity (must be >= 1, default: 1) |
| `glref` | string | General ledger reference |

#### Location
| Property | Type | Description |
|----------|------|-------------|
| `pcd` | int32 | PCode (preferred — most precise) |
| `npa` | int32 | NPANXX number |
| `fips` | string | FIPS code |
| `addr` | string | Street address |
| `city` | string | City name |
| `st` | string | State abbreviation |
| `zip` | string | Postal code |
| `ctry` | string | Country ISO code |
| `cnty` | string | County name |
| `int` | bool | Within city limits (default: true) |
| `geo` | bool | Geocode this address (default: false) |

Location resolution priority: PCode > FIPS > NPANXX > address fields. Set `geo: true` to geocode address fields into a PCode.

#### TaxExemption
| Property | Type | Description |
|----------|------|-------------|
| `loc` | Location | Exemption jurisdiction |
| `tpe` | int16 | Tax type to exempt (mutually exclusive with `cat`) |
| `cat` | int16 | Tax category to exempt (mutually exclusive with `tpe`) |
| `lvl` | int16 | Tax level ID |
| `dom` | int16 | Exemption domain (see enum below) |
| `scp` | int16 | Exemption scope (see enum below) |
| `frc` | bool | Override level exempt flag on wildcard exemptions |
| `exnb` | bool | Exempt non-billable taxes |
| `allovcnty` | bool | Include overlapping counties when domain=local |
| `preclude` | bool | Preclude exemption from applying |

#### TaxOverride
| Property | Type | Description |
|----------|------|-------------|
| `loc` | Location | Override jurisdiction |
| `scp` | int16 | Scope: 0=Country, 1=State, 2=County, 3=City |
| `tid` | int16 | Tax type ID |
| `lvl` | int16 | Tax level: 0=Federal, 1=State, 2=County, 3=City |
| `lvlExm` | bool | Tax can be exempted using level exemptions |
| `brkt` | TaxBracket[] | Rate/bracket information |

#### TaxBracket
| Property | Type | Description |
|----------|------|-------------|
| `rate` | double | Tax rate (0-1 for rated taxes, non-negative) |
| `max` | double | Maximum base for this rate bracket |

#### SafeHarborOverride
| Property | Type | Description |
|----------|------|-------------|
| `sh` | int16 | Safe harbor type: 1=Cellular, 2=VoIP, 4=Paging |
| `old` | double | Original federal TAM value to replace |
| `new` | double | New TAM value |

#### RequestConfig
| Property | Type | Description |
|----------|------|-------------|
| `retnb` | bool | Return non-billable taxes (overrides account setting) |
| `retext` | bool | Return extended tax data |
| `incrf` | bool | Return reporting information |

#### CalcTaxesResponse
| Property | Type | Description |
|----------|------|-------------|
| `inv` | InvoiceResult[] | Results per invoice |
| `err` | Error[] | Errors (if any) |

#### InvoiceResult
| Property | Type | Description |
|----------|------|-------------|
| `doc` | string | Document code |
| `itms` | LineItemResult[] | Per-line-item results |
| `summ` | SummarizedTax[] | Summarized invoice taxes |
| `err` | Error[] | Errors |
| `incrf` | ReportingInformation | Reporting info |

#### LineItemResult
| Property | Type | Description |
|----------|------|-------------|
| `ref` | string | Reference ID |
| `base` | double | Base sale amount (for tax-inclusive items) |
| `txs` | Tax[] | Generated taxes |
| `err` | Error[] | Errors |

#### Tax
| Property | Type | Description |
|----------|------|-------------|
| `bill` | bool | Billable to customer |
| `cmpl` | bool | Reportable to jurisdiction |
| `tm` | double | Taxable measure |
| `calc` | int16 | Calculation type |
| `cat` | string | Tax category name |
| `cid` | int16 | Tax category ID |
| `name` | string | Tax name |
| `exm` | double | Exempt sale amount |
| `lns` | int32 | Lines |
| `min` | double | Minutes |
| `pcd` | int32 | Reporting jurisdiction PCode |
| `taxpcd` | int32 | Taxing jurisdiction PCode (extended only) |
| `rate` | double | Tax rate |
| `sur` | bool | Is surcharge |
| `tax` | double | Tax amount |
| `lvl` | int16 | Tax level ID |
| `tid` | int16 | Tax type ID |
| `usexm` | bool | User-exempted flag (extended only) |
| `notax` | bool | No-tax entry flag (extended only) |
| `trans` | int16 | Transaction type used (extended only) |
| `svc` | int16 | Service type used (extended only) |
| `chg` | double | Charge used to calculate (extended only) |

#### SummarizedTax
| Property | Type | Description |
|----------|------|-------------|
| `max` | double | Max base for bracket |
| `min` | double | Min base for bracket |
| `tchg` | double | Total charge amount |
| `calc` | int16 | Calculation type |
| `cat` | string | Tax category name |
| `cid` | int16 | Tax category ID |
| `name` | string | Tax name |
| `exm` | double | Exempt sale amount |
| `lns` | int32 | Lines |
| `mins` | double | Minutes |
| `pcd` | int32 | Reporting jurisdiction PCode |
| `rate` | double | Tax rate |
| `sur` | bool | Is surcharge |
| `tax` | double | Tax amount |
| `lvl` | int16 | Tax level ID |
| `tid` | int16 | Tax type ID |

#### CommitRequest
| Property | Type | Description |
|----------|------|-------------|
| `doc` | string | Document code |
| `cmmt` | bool | true=commit, false=uncommit |
| `opt` | KeyValuePair[] | Override OptionalFields in reports |

#### CommitResponse
| Property | Type | Description |
|----------|------|-------------|
| `ok` | bool | Success flag |
| `err` | Error[] | Errors |

#### Error
| Property | Type | Description |
|----------|------|-------------|
| `code` | int32 | Error code |
| `msg` | string | Error message |

#### GeocodeRequest
| Property | Type | Description |
|----------|------|-------------|
| `ref` | string | Optional reference ID |
| `lat` | double | Latitude (use lat/long OR address, not both) |
| `long` | double | Longitude |
| `addr` | string | Street address |
| `city` | string | City |
| `st` | string | State |
| `zip` | string | Postal code |

#### GeocodeResult
| Property | Type | Description |
|----------|------|-------------|
| `ref` | string | Reference ID from input |
| `cass` | Address | CASS-validated address |
| `cBlk` | int32 | Census block |
| `cTrc` | int32 | Census tract |
| `cnty` | string | County |
| `feat` | int32 | Feature ID |
| `fips` | string | FIPS code |
| `inc` | bool | Within city limits |
| `jur` | string | Tax jurisdiction name |
| `lat` | double | Latitude |
| `long` | double | Longitude |
| `pcd` | int32 | PCode |
| `scr` | double | Match accuracy score |
| `err` | string | Error message |

#### PCodeLookupRequest
| Property | Type | Description |
|----------|------|-------------|
| `CountryIso` | string | 3-char country ISO |
| `State` | string | 2-char state abbreviation |
| `County` | string | County name |
| `City` | string | City name |
| `ZipCode` | string | Zip code |
| `BestMatch` | bool | true=best match, false=exact only |
| `LimitResults` | int32 | Max results |
| `NpaNxx` | string | NPANXX code (use `*` suffix for range) |
| `Fips` | string | 5-digit FIPS code (use `*` suffix for range) |

#### PCodeLookupResult
| Property | Type | Description |
|----------|------|-------------|
| `LocationData` | LocationItem[] | Matching locations |
| `MatchCount` | int32 | Number of matches |
| `InputMatchType` | string | "Exact" or "Best" |
| `MatchTypeApplied` | string | Match type actually used |
| `ResultsLimit` | int32 | Max results applied |

#### KeyValuePair
| Property | Type | Description |
|----------|------|-------------|
| `key` | string | Key |
| `val` | string | Value |

#### BillingPeriod
| Property | Type | Description |
|----------|------|-------------|
| `month` | int32 | Month (1=January) |
| `year` | int32 | 4-digit year |

#### ReportingInformation
| Property | Type | Description |
|----------|------|-------------|
| `acct` | string | Account ID |
| `custref` | string | Customer reference |
| `invn` | string | Invoice number |
| `bcyc` | string | Bill cycle |
| `ccycd` | string | Currency code |
| `ccydesc` | string | Currency description |

### Enums and Constants

**Customer Type** (`cust`): 0=Residential, 1=Business, 2=Senior Citizen, 3=Industrial

**Sale Type** (`sale`): 0=Wholesale, 1=Retail, 2=Consumed, 3=VendorUse

**Discount Type** (`disc`): 0=None, 1=Retail Product, 2=Manufacturer Product, 3=Account Level, 4=Subsidized, 5=Goodwill

**Tax Level** (`lvl`): 0=Federal, 1=State, 2=County, 3=City

**Business Class** (`bscl`): 0=ILEC, 1=CLEC

**Service Class** (`svcl`): 0=Primary Local, 1=Primary Long Distance

**Safe Harbor Type** (`sh`): 1=Cellular, 2=VoIP, 4=Paging

**Exemption Domain** (`dom`): Jurisdiction level where exemption must match taxing jurisdiction

**Exemption Scope** (`scp`): Defines tax levels considered as exemption candidates

**Override Scope** (`scp` on TaxOverride): 0=Country, 1=State, 2=County, 3=City

**Pro-rated Adjustment** (`proadj`): 0=None, 1=Exclude non-proratable fixed taxes, 2=Include non-proratable fixed taxes

**ClientProfileConfigTypes**: All, Configuration, Bundle, Exclusion, Override, Nexus, Exemption

**SelfTaxAlgorithm**: Individual, Aggregate

**TaxOnTaxAlgorithm**: Once, IterateOnTaxAmount, IterateOnTaxableMeasure

### Common Patterns

#### Basic CalcTaxes Request
```json
{
  "cmpn": {
    "bscl": 1, "svcl": 0, "fclt": true, "frch": true, "reg": false
  },
  "inv": [{
    "doc": "INV-001",
    "bill": { "pcd": 4133800 },
    "cust": 0,
    "date": "2024-01-15T00:00:00Z",
    "itms": [{
      "ref": "Line1",
      "from": { "pcd": 4133800 },
      "to": { "pcd": 4133800 },
      "chg": 100.00,
      "line": 1,
      "tran": 19,
      "serv": 6,
      "sale": 1
    }]
  }]
}
```

#### Commit Workflow
1. Send CalcTaxes with `"cmmt": false` (or omit — default is false)
2. Review results
3. POST to `/api/v2/afc/commit` with `{"doc": "INV-001", "cmmt": true}`
4. To uncommit: `{"doc": "INV-001", "cmmt": false}`

#### Exemption Example
```json
"exms": [{
  "loc": { "pcd": 4133800 },
  "tpe": 1,
  "lvl": 1,
  "dom": 0,
  "scp": 0
}]
```

#### P2P (Point-to-Point) Transactions
Use different `from` and `to` locations on line items for interstate/intercity calls. The engine determines jurisdiction based on both endpoints.

### Important API Notes

- **Invoice Mode** (`invm: true`): All line items in an invoice are taxed together as a single transaction. When false, each line item is taxed independently.
- **Tax Inclusive** (`incl: true`): The charge amount includes tax. The engine back-calculates the base amount.
- **Extended Data** (`cfg.retext: true`): Returns additional fields on Tax objects (`taxpcd`, `usexm`, `notax`, `trans`, `svc`, `chg`).
- **Non-Billable Taxes** (`cfg.retnb: true`): Returns taxes not typically billed to customers (compliance-only taxes).
- **Geocoding on Location**: Set `geo: true` on a Location to have the address geocoded to a PCode during tax calculation.
- **PCode Wildcards**: Use `*` suffix on Fips/NpaNxx in PCodeLookupRequest to match a range of values.
- **Document Code**: Required for commit/uncommit. Use a unique identifier per invoice for auditing.

> For deeper detail, explicitly ask Code to read `swagger.json`, the SDK docs in `afc_saaspro_tax/afc_rest_apis/SDK/csharp-netcore/docs/`, JSON samples in `afc_saaspro_tax/afc_rest_apis/JSON/`, or the offline HTML docs in `docs/`. These are ignored by default to conserve context.

## Git & GitLab

This project is hosted on GitLab at `git@gitlab.com:avalara3/comms-connector-poc.git`. Use the default SSH host `gitlab.com` which maps to the **JRSarusinc** work account (key: `~/.ssh/id_ed25519`). All git push/pull operations should use this SSH remote — do not use HTTPS or the personal `gitlab-personal` host alias.

## Salesforce Metadata Deployment Rules

Hard-won lessons from deploying the `ATC_Tax_Line__c` custom object. These apply to any Salesforce metadata work in this repo.

### Field-Level Security (FLS) is NEVER auto-granted by Metadata API

When you deploy new custom fields via `sf project deploy`, Salesforce does **not** automatically grant FLS to any profile — not even System Administrator. Optional fields (those without `<required>true</required>`) will be invisible in the Lightning UI because they return null to the browser, and Lightning hides null fields.

**Every time you add a new optional custom field, you must also:**
1. Add `fieldPermissions` to `salesforce_metadata/profiles/Admin.profile-meta.xml`
2. Deploy the profile in the same operation

Example entry to add for each field:
```xml
<fieldPermissions>
    <editable>true</editable>
    <field>ATC_Tax_Line__c.My_New_Field__c</field>
    <readable>true</readable>
</fieldPermissions>
```

Deploy both together:
```bash
sf project deploy start --metadata "CustomObject:ATC_Tax_Line__c" --metadata "Profile:Admin" -o john.romano@sarusinc.com.sf
```

**Required fields** (`<required>true</required>`) bypass FLS automatically and are always visible. Optional fields do not.

### FlexiPage activation lives in the CustomObject, not the FlexiPage

Activating a Lightning Record Page as org default is **not** done inside the FlexiPage XML. It lives in the CustomObject metadata as `<actionOverrides>`:

```xml
<!-- In salesforce_metadata/objects/MyObject__c/MyObject__c.object-meta.xml -->
<actionOverrides>
    <actionName>View</actionName>
    <comment>Action override created by Lightning App Builder during activation.</comment>
    <content>My_Record_Page</content>
    <formFactor>Large</formFactor>
    <skipRecordTypeSelect>false</skipRecordTypeSelect>
    <type>Flexipage</type>
</actionOverrides>
```

Deploy the FlexiPage and CustomObject together when activating:
```bash
sf project deploy start --metadata "FlexiPage:My_Record_Page" --metadata "CustomObject:MyObject__c" -o john.romano@sarusinc.com.sf
```

### Lightning browser cache vs. FLS changes

Hard refresh (`Ctrl+F5`) does **not** clear Salesforce's Lightning component cache. After granting new FLS permissions, users must log out and back in (or open an incognito window) to see the changes. The CLI/API will show the correct data immediately; only the browser session is stale.

### `force:detailPanel` renders fields from the Page Layout

The `force:detailPanel` component in a FlexiPage renders whatever fields are in the assigned Page Layout. If the Page Layout was never deployed to the org, the component falls back to showing only required fields and system fields. Always deploy the Layout alongside the FlexiPage.

### Deployment checklist for a new custom object

When deploying a new custom object with a Lightning Record Page, deploy these in order:

1. `CustomObject` (object + all fields)
2. `Layout` (page layout with fields arranged)
3. `Profile:Admin` (FLS for all optional fields)
4. `FlexiPage` + `CustomObject` together (FlexiPage components + actionOverrides activation)

## Architecture Notes

- This is primarily a **documentation and SDK distribution repo**, not an application. Most code is auto-generated client libraries.
- Sample code in `afc_saaspro_geo/sample_code/` covers .NET, Java, PHP, SOAP, and batch geocoding scenarios.
- SOAP API samples are XML-based and found under `afc_saaspro_tax/afc_soap_apis/` and `afc_saaspro_geo/sample_code/SOAP/`.
- Manuals are PDF/document files in `manuals/` directories under each product area.
- Support docs with tax type/category references are under `support_docs/` directories.
