# Money concepts for comparing co-op offers

These lessons are short and written in plain English. Each one ends with a
tiny worked example. All the numbers come from this project's calculator,
and they are **estimates**: simplified 2026 tax rules and rough 2026 rent and
transit figures, not payroll advice. Every offer here is a **SYNTHETIC
EXAMPLE** made up for teaching.

One convention is used everywhere: **a month is 4.333 weeks** (52 weeks ÷ 12
months). A 16-week term is therefore 16 ÷ 4.333 = 3.6926 months.

---

## 1. Gross pay vs net pay

**Gross pay** is the headline number in the offer: your rate × your hours.
**Net pay** is the amount that actually reaches your bank account. To get it,
your employer takes off income tax, CPP (QPP in Quebec), EI, and in Quebec
also QPIP. Payroll sends those amounts to the government for you.

> *Worked example (synthetic).* $25/hour × 40 hours × 16 weeks = **$16,000
> gross** in Waterloo. The estimated deductions are $3,286.19, so net pay is
> **$12,713.81**. About one dollar in five never reaches your account.

## 2. CPP: the Canada Pension Plan

CPP is a pension you pay into with every paycheque. It is not a fee you lose:
it builds up a retirement benefit you collect later. You pay 5.95% of your
pay above a small exemption ($3,500 a year, which a 16-week term prorates to
$1,076.92). CPP stops once you hit the **annual maximum**. A short co-op term
pays far less than a full year would, because the maximum is per year and
you only worked part of it. In Quebec, the QPP does the same job at 6.4%.

> *Worked example (synthetic).* 5.95% × ($16,000 − $1,076.92) = **$887.92**
> for the term. A full year's maximum would be about $4,230, so this term is
> nowhere near it.

## 3. EI: Employment Insurance

EI is insurance. If you lose a job or take parental leave, it pays you part
of your wages for a while. You pay 1.63% of your pay (1.30% in Quebec, which
also has its own QPIP parental plan). EI also has an annual maximum, and a
normal co-op term never gets close to it.

> *Worked example (synthetic).* 1.63% × $16,000 = **$260.80** for the term.

## 4. Marginal vs average tax rate (and the bracket myth)

Income tax works in **slices**. The first slice of a year's income is taxed
at a low rate, the next slice at a higher rate, and so on. Your **marginal
rate** is the rate on your *next* dollar. Your **average rate** is your total
tax divided by your total income. The average is always lower.

**The myth:** "a raise could push me into a higher bracket and I'd take home
less." **Wrong.** The higher rate applies only to the dollars *above* the
bracket line. The dollars below it are taxed exactly as before. A raise never
lowers your pay after tax.

> *Worked example (synthetic).* $25/hour annualises to $52,000 a year. On
> that, the marginal rate is about **19.05%** (14% federal + 5.05% Ontario),
> but the average income-tax rate is only about **13.4%**. Now picture a raise
> that moves you $100 past Ontario's $53,891 line. Only that $100 is taxed
> at the higher 23.15% (14% + 9.15%), so it costs you $23.15. You keep the
> other $76.85, and nothing else changes.

## 5. Annualising: why tax uses a full year

Tax brackets are set per year, but a co-op term is only part of one. Payroll
asks, "what if you earned this much all year?" It works out a year's tax at
that pay, then takes off the share for this paycheque. This tool does the
same thing: it scales the term up to a year, applies the brackets, and
scales the result back down.

> *Worked example (synthetic).* $16,800 for 16 weeks × 52 ÷ 16 = $54,600 a
> year. The federal tax on $54,600 is $5,340.72, and × 16/52 that comes to
> **$1,643.30** for the term. If you taxed $16,800 as though it were the
> whole year, you'd get only about $50 of federal tax, because most of it
> would hide under the basic personal amount. That is not what your
> paycheques will show. (If this is your only job all year, some of what
> was withheld may come back as a refund at tax time.)

## 6. The same salary buys a different life in different cities

Three things change when the same pay moves to another city: **rent**,
**transit**, and **provincial tax**. Rent is usually the biggest by far.

> *Worked example (synthetic, using city presets).* $25/hour × 40 hours × 16
> weeks, typical one-bedroom rent, and a transit pass:
>
> | City | Net pay (term) | Living costs / month | **Take-home / month** |
> |---|---:|---:|---:|
> | Calgary (AB) | $12,600.45 | $1,868.00 | **$1,544.36** |
> | Waterloo (ON) | $12,713.81 | $2,000.00 | **$1,443.06** |
> | Montreal (QC) | $12,039.23 | $1,854.00 | **$1,406.37** |
> | Ottawa (ON) | $12,713.81 | $2,186.00 | **$1,257.06** |
> | Toronto (ON) | $12,713.81 | $2,610.00 | **$833.06** |
> | Vancouver (BC) | $12,698.42 | $2,810.00 | **$628.89** |
>
> The pay is identical in every row, but take-home ranges from $629 to $1,544
> a month. Quebec takes more in tax and payroll deductions, yet Montreal's
> lower rent makes up for most of it. Use `breakeven` to ask, "how much more
> would Toronto have to pay to match Waterloo?"

## 7. One-time costs vs recurring costs, and why amortising matters

**Recurring** costs come back every month: rent, transit, your phone.
**One-time** costs happen once: a damage deposit, a moving truck, furniture.
To compare them fairly, spread (**amortise**) the one-time cost over the
months it serves. The same bill hurts more on a short term than on a long
one.

> *Worked example.* A $1,200 move spread over a 16-week term (3.69 months) is
> **$324.98 a month**. Spread over a 24-week term (5.54 months), it is
> **$216.65 a month**. The tool shows the one-time total *and* the monthly
> share, and takes the full amount off whole-term take-home.

## 8. Monthly vs whole-term comparisons

Offers can have different term lengths. A longer term always *looks* bigger
on whole-term totals, simply because it lasts longer. That is why the tool
ranks by **take-home per month** and also shows per week.

> *Worked example (synthetic, Waterloo, $1,200 rent).* $25/hour for 16
> weeks gives $7,913.44 for the term, or **$2,143.06 a month**. $23/hour for
> 24 weeks gives $10,461.45 for the term, a bigger total, but only
> **$1,888.73 a month**. Per month, the shorter offer is better. Whether you
> want the longer job is a separate question, about the job itself.

## 9. Lump sums: why they must not be folded into monthly pay

A signing bonus or relocation payment arrives **once**. If you divide it
into your monthly pay, a one-off windfall starts to look like a raise you'll
get every month. It also hides the fact that bonuses are taxed. The tool
keeps lump sums on their own line, estimates the tax using the "bonus
method" (tax on annual pay + bonus, minus tax on annual pay alone), and only
then adds them to whole-term take-home.

> *Worked example (synthetic).* A $3,000 signing bonus on a $25/hour,
> 16-week Waterloo offer has about $616.97 of estimated tax, so you keep
> **$2,383.03**. It raises take-home per month from $2,143.06 to $2,788.41
> *for this term only*. If you treated it as $812/month of extra gross pay,
> you'd overstate both the bonus and your next offer's "pay cut". A relocation
> *reimbursement* of real receipts may not be taxable at all. In that case,
> mark it `"taxable": false`.

## 10. Five beginner mistakes to skip

1. **Comparing hourly rates instead of take-home.** $28/hour in Toronto
   leaves less than $24/hour in Waterloo in this project's sample
   ($677.93 vs $1,640.89 a month). Rent decides most comparisons.
2. **Comparing whole-term totals across different term lengths.** Use the
   per-month or per-week figure.
3. **Thinking a higher bracket taxes all your pay more.** It only taxes the
   dollars above the line (lesson 4).
4. **Forgetting one-time costs, or counting a bonus as a raise.** Spread
   the move over the term, and keep the bonus on its own line (lessons 7
   and 9).
5. **Trusting a ranking that is closer than your guesses.** If two offers
   are within $25 a month, or a $200 change in your rent guess flips the
   ranking, the money is a tie. Choose on the work, the team and what you'll
   learn.

---

*Estimates only: simplified 2026 tax rules and rough 2026 planning figures
for rent and transit. This is not payroll, tax or financial advice. All
offers above are SYNTHETIC EXAMPLES.*
