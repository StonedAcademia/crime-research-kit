# Evidence board: Synthetic Case

## Source ledger

| ID | Grade | Type | Title | Publisher | Date |
|---|---|---|---|---|---|
| SDEMO0001 | B | news_article | Synthetic local report on the formation of the Harbor Study Circle | Demo Local News | 1978-04-12 |

## Entities

| ID | Type | Name | Roles | Privacy | Public |
|---|---|---|---|---|---|
| EDEMO_LEADER | person | Demo Leader | founder | public_figure | True |
| EDEMO_GROUP | group | Harbor Study Circle | group | unknown | True |

## Events

| ID | Date | Type | Title | Status | Sources |
|---|---|---|---|---|---|
| EVDEMO0001 | 1978-04-00 | founding | Harbor Study Circle begins meeting | single_source | SDEMO0001 |

## Event links

| ID | Entity | Relation | Event | Basis | Status | Public |
|---|---|---|---|---|---|---|

## Relationships

| ID | Source | Relation | Target | Status | Sources |
|---|---|---|---|---|---|
| RDEMO0001 | EDEMO_LEADER | founded | EDEMO_GROUP | single_source | SDEMO0001 |

## Claims by status

### single_source

| ID | Confidence | Claim | Sources | Public |
|---|---|---|---|---|
| CDEMO0001 | 0.62 | The source states that the Harbor Study Circle began meeting in 1978. | SDEMO0001 | True |

## Redactions / public-output exclusions

| Record | Field | Reason | Replacement |
|---|---|---|---|
