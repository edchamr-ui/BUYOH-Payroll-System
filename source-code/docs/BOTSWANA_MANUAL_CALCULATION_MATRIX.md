# Botswana PAYE — Verified Manual Calculation Matrix

## Document control

| Field | Value |
|---|---|
| Country | Botswana |
| Currency | Botswana pula (BWP) |
| Engine | `BOTSWANA_PAYE` |
| Country code | `BW` |
| Payroll frequency | Monthly |
| Tax-year cycle | 1 July–30 June |
| Engine scope | Resident and non-resident employees |
| Employee statutory contribution | None configured |
| Employer statutory contribution | None configured |
| Payroll levy | None configured |
| Calculation precision | Monetary results persisted to 2 decimal places |
| Verification suite | 72 tests passing |
| Status | Implementation-verified; legal source version must remain documented |

## Purpose

This document independently reconciles the Botswana payroll engine against
manual calculations and the permanent automated test suite.

It verifies:

- Resident progressive PAYE
- Non-resident progressive PAYE
- Monthly tax-band boundaries
- Regular commission spread-back
- Occasional irregular remuneration
- Tax-deductible pension treatment
- July–June year-to-date accumulation
- Rounding, deductions, net pay, and employer cost
- Provisional prior-year rule fallback

## Compliance boundary

The implementation identifies its resident rates as the verified BURS
2026/27 table. The integration fixture currently stores the rule as:

| Field | Stored value |
|---|---|
| Rule name | Botswana BURS PAYE 2025 |
| Effective from | 1 July 2025 |
| Effective to | 30 June 2027 |
| Currency | BWP |
| PAYE enabled | Yes |

The fixture’s name and two-year effective range do not perfectly describe a
single Botswana tax year. Before production deployment, the imported
statutory preset must preserve the exact BURS publication title, issue date,
source URL, tax year, and effective dates.

This matrix verifies the implemented calculations. It does not replace
professional tax advice or statutory-source review.

## Official reference points

- Botswana Unified Revenue Service PAYE:
  https://www.burs.org.bw/index.php/tax/income-tax/pay-as-you-earn
- Botswana Unified Revenue Service tax downloads:
  https://www.burs.org.bw/index.php/tax/tax-downloads
- Botswana Unified Revenue Service tax calculator:
  https://www.burs.org.bw/index.php/my-services/tax-calculator

## 1. Resident annual PAYE bands

The resident monthly calculation corresponds to these annual bands:

| Band | Annual taxable income | Rate |
|---:|---:|---:|
| 1 | P0–P48,000 | 0% |
| 2 | Over P48,000–P84,000 | 5% |
| 3 | Over P84,000–P120,000 | 12.5% |
| 4 | Over P120,000–P156,000 | 18.75% |
| 5 | Over P156,000–P400,000 | 25% |
| 6 | Over P400,000 | 27.5% |

## 2. Resident monthly PAYE bands

| Band | Monthly taxable income | Manual calculation |
|---:|---:|---|
| 1 | P0–P4,000 | P0 |
| 2 | Over P4,000–P7,000 | 5% of excess over P4,000 |
| 3 | Over P7,000–P10,000 | P150 + 12.5% of excess over P7,000 |
| 4 | Over P10,000–P13,000 | P525 + 18.75% of excess over P10,000 |
| 5 | Over P13,000–P33,333.33 | P1,087.50 + 25% of excess over P13,000 |
| 6 | Over P33,333.33 | Annualize income, calculate annual PAYE, then divide by 12 |

## 3. Resident boundary matrix

| Monthly taxable income | Manual PAYE | Net after PAYE | Verification |
|---:|---:|---:|---|
| P4,000.00 | P0.00 | P4,000.00 | Exact zero-rate ceiling |
| P4,001.00 | P0.05 | P4,000.95 | First pula in 5% band |
| P7,000.00 | P150.00 | P6,850.00 | End of 5% band |
| P10,000.00 | P525.00 | P9,475.00 | End of 12.5% band |
| P13,000.00 | P1,087.50 | P11,912.50 | End of 18.75% band |
| P18,000.00 | P2,337.50 | P15,662.50 | 25% band |
| P34,000.00 | P6,354.17 | P27,645.83 | 27.5% band |

### P18,000 resident calculation

```text
P4,000 × 0%                       = P0.00
P3,000 × 5%                       = P150.00
P3,000 × 12.5%                    = P375.00
P3,000 × 18.75%                   = P562.50
(P18,000 − P13,000) × 25%         = P1,250.00
                                          ─────────
PAYE                                      P2,337.50
Net pay: P18,000 − P2,337.50             P15,662.50
```

### P34,000 resident calculation

```text
Annualized income: P34,000 × 12           = P408,000.00

P36,000 × 5%                              = P1,800.00
P36,000 × 12.5%                           = P4,500.00
P36,000 × 18.75%                          = P6,750.00
P244,000 × 25%                            = P61,000.00
P8,000 × 27.5%                            = P2,200.00
                                                   ──────────
Annual PAYE                                      P76,250.00
Monthly PAYE: P76,250 ÷ 12                       P6,354.17
```

## 4. Non-resident PAYE bands

Non-resident PAYE is progressive. The 5% rate applies only to the first
P7,000.

| Band | Monthly taxable income | Manual calculation |
|---:|---:|---|
| 1 | P0–P7,000 | 5% of taxable income |
| 2 | Over P7,000–P10,000 | P350 + 12.5% of excess over P7,000 |
| 3 | Over P10,000–P13,000 | P725 + 18.75% of excess over P10,000 |
| 4 | Over P13,000–P33,333 | P1,287.50 + 25% of excess over P13,000 |
| 5 | Over P33,333 | P6,370.75 + 27.5% of excess over P33,333 |

## 5. Non-resident calculation matrix

| Monthly taxable income | Manual PAYE | Net after PAYE |
|---:|---:|---:|
| P7,000.00 | P350.00 | P6,650.00 |
| P10,000.00 | P725.00 | P9,275.00 |
| P13,000.00 | P1,287.50 | P11,712.50 |
| P89,000.00 | P21,679.18 | P67,320.82 |

### P89,000 non-resident calculation

```text
P7,000 × 5%                       = P350.00
P3,000 × 12.5%                    = P375.00
P3,000 × 18.75%                   = P562.50
P20,333 × 25%                     = P5,083.25
(P89,000 − P33,333) × 27.5%       = P15,308.425
                                          ───────────
Unrounded PAYE                            P21,679.175
Persisted PAYE                            P21,679.18
```

The automated regression test notes that a published worked example contains
a small arithmetic inconsistency. The engine follows the configured
progressive bands and produces P21,679.18.

## 6. Commission spread-back calculation

Scenario:

| Component | Amount |
|---|---:|
| Current basic salary | P4,000.00 |
| Current commission | P700.00 |
| Prior regular taxable income | P4,500.00 |
| Prior regular PAYE | P25.00 |
| Payments already elapsed | 1 |
| Projected annual regular income | P49,200.00 |

Calculation:

```text
Current regular remuneration              P4,700.00
Cumulative remuneration                   P9,200.00
Average over two payments                 P4,600.00
PAYE on average remuneration              P30.00
Cumulative PAYE: P30 × 2                  P60.00
Less PAYE already withheld                P25.00
                                                  ──────
Current regular PAYE                      P35.00
Irregular PAYE                            P0.00
```

This confirms that commission is spread back across elapsed payments instead
of being treated as an occasional bonus.

## 7. Occasional bonus calculation

Scenario:

| Component | Amount |
|---|---:|
| Monthly basic salary | P4,000.00 |
| Annual regular income | P48,000.00 |
| Occasional bonus | P4,000.00 |
| Gross pay in bonus month | P8,000.00 |

Calculation:

```text
Annual PAYE without bonus                 P0.00
Annual income with bonus                  P52,000.00
Taxable excess: P52,000 − P48,000         P4,000.00
Bonus PAYE: P4,000 × 5%                   P200.00

Regular PAYE                              P0.00
Irregular PAYE                            P200.00
Total PAYE                                P200.00
Net pay: P8,000 − P200                    P7,800.00
```

## 8. Large occasional bonus calculation

| Component | Amount |
|---|---:|
| Monthly basic salary | P3,600.00 |
| Projected annual regular income | P43,500.00 |
| Occasional bonus | P20,000.00 |
| Bonus-month gross pay | P23,600.00 |

```text
Annual income including bonus             P63,500.00
Taxable excess over P48,000               P15,500.00
Irregular PAYE: P15,500 × 5%              P775.00
Net pay: P23,600 − P775                   P22,825.00
```

## 9. Approved pension and commission production case

| Component | Amount |
|---|---:|
| Basic salary | P18,000.00 |
| Commission | P700.00 |
| Gross pay | P18,700.00 |
| Approved tax-deductible pension | P200.00 |
| Taxable income | P18,500.00 |
| Regular PAYE | P2,462.50 |
| Irregular PAYE | P0.00 |
| Total deductions | P2,662.50 |
| Net pay | P16,037.50 |
| Employer statutory contribution | P0.00 |
| Employer cost | P18,700.00 |

Reconciliation:

```text
Taxable income:
P18,000 + P700 − P200                     = P18,500.00

PAYE:
P1,087.50 + (P18,500 − P13,000) × 25%     = P2,462.50

Total deductions:
P2,462.50 + P200                          = P2,662.50

Net pay:
P18,700 − P2,662.50                       = P16,037.50
```

The pension reduces taxable income and also reduces net pay.

## 10. July–June YTD behavior

Botswana YTD accumulation begins on 1 July and ends on 30 June.

For a calculation dated 30 June 2026, persisted records from July 2025
through June 2026 are eligible. A June 2025 record is excluded.

Verified example:

| Item | Amount |
|---|---:|
| July 2025 regular taxable income | P4,500.00 |
| May 2026 regular taxable income | P5,000.00 |
| YTD regular taxable income | P9,500.00 |
| July 2025 regular PAYE | P25.00 |
| May 2026 regular PAYE | P50.00 |
| YTD regular PAYE | P75.00 |
| Elapsed payments | 2 |

For a calculation dated 31 July 2026, June 2026 history is excluded and the
new tax year begins with zero YTD income, PAYE, and elapsed payments.

## 11. Complete production-run reconciliation

| Measure | Three-employee total |
|---|---:|
| Employees | 3 |
| Basic salaries | P29,000.00 |
| Allowances | P4,700.00 |
| Gross pay | P33,700.00 |
| Regular PAYE | P2,812.50 |
| Irregular PAYE | P200.00 |
| Combined PAYE | P3,012.50 |
| Employee statutory contribution | P0.00 |
| Employer statutory contribution | P0.00 |
| Payroll levy | P0.00 |
| Other deductions | P200.00 |
| Total deductions | P3,212.50 |
| Net pay | P30,487.50 |
| Employer cost | P33,700.00 |

Reconciliation:

```text
Combined PAYE:
P2,812.50 + P200.00                       = P3,012.50

Total deductions:
P3,012.50 + P200.00                       = P3,212.50

Net pay:
P33,700.00 − P3,212.50                    = P30,487.50

Employer cost:
P33,700.00 + P0.00                        = P33,700.00
```

## 12. Provisional-rule fallback

When no rule covers the calculation date, the payroll service may select the
most recent prior rule provisionally.

The processing result must expose:

- `provisional_rule_used = True`
- The calculation date
- The prior rule’s `effective_to` date
- A `PROVISIONAL FALLBACK` audit warning
- The message that prior-year statutory rates were used

A provisional calculation must not be presented as fully verified current-year
compliance. Updated BURS rates must be reviewed and installed as soon as they
become available.

## 13. Automated-test traceability

| Matrix section | Automated verification |
|---|---|
| Resident boundaries | `test_resident_monthly_paye_boundaries` |
| Non-resident bands | `test_non_resident_monthly_paye` |
| Commission spread-back | `test_commission_uses_burs_spread_back_method` |
| P4,000 bonus | `test_bonus_uses_annual_tax_difference` |
| P20,000 bonus | `test_large_occasional_bonus_matches_burs_example_12` |
| Persisted payroll | `test_process_period_persists_botswana_paye_and_audit` |
| July–June YTD | `test_botswana_ytd_uses_persisted_july_to_june_history` |
| July reset | `test_botswana_ytd_resets_in_july` |
| Production components | `test_processes_multiple_employees_and_recurring_components` |
| Assignment dates | `test_excludes_inactive_and_out_of_date_assignments` |
| Provisional fallback | `test_prior_year_fallback_is_exposed_and_audited` |
| Payslip/report totals | `test_botswana_payslip_reporting.py` |

## 14. Final verification status

The Botswana implementation is verified for the currently configured
contracts when all of the following remain true:

- Currency is BWP
- Residency is explicitly `Resident` or `Non-Resident`
- The resident configuration contains exactly six verified bands
- The configured rates match 0%, 5%, 12.5%, 18.75%, 25%, and 27.5%
- Botswana employee and employer statutory contributions remain zero
- The payroll levy remains zero
- The July–June YTD calculation remains enabled
- Provisional-rule use remains visible and audited
- The complete automated suite remains green

Any legislative or BURS-table change requires a new versioned statutory rule,
updated effective dates, recalculated matrix values, and regression tests
before production use.
