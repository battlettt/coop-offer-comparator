/* coop-offer-comparator demo. Vanilla JS, no dependencies, no build step,
   no network calls.

   The first half of this file (CORE) is a line-for-line port of the Python
   package: coop_compare/tax_tables.py, presets.py, model.py (validation)
   and calc.py (all the math). tests/test_parity.py runs this file under
   Node and checks that it gives exactly the same numbers, issues and
   verdicts as Python on shared fixtures. If you change the math in one
   place, change it in the other.

   Every figure is an ESTIMATE, not payroll or tax advice. */
(function (root) {
  'use strict';

  /* ===================== CORE: tables (tax_tables.py) ===================== */
  var TABLES = {
    tax_year: 2026,
    weeks_per_year: 52,
    weeks_per_month: 4.333,
    federal: {
      brackets: [[58523, 0.14], [117045, 0.205], [181440, 0.26], [258482, 0.29], [null, 0.33]],
      basic_personal_amount: 16452
    },
    quebec_abatement: 0.165,
    provinces: {
      'Ontario': {
        code: 'ON',
        brackets: [[53891, 0.0505], [107785, 0.0915], [150000, 0.1116], [220000, 0.1216], [null, 0.1316]],
        basic_personal_amount: 12989
      },
      'British Columbia': {
        code: 'BC',
        brackets: [[50363, 0.0506], [100728, 0.077], [115648, 0.105], [140430, 0.1229], [190405, 0.147], [265545, 0.168], [null, 0.205]],
        basic_personal_amount: 12932
      },
      'Quebec': {
        code: 'QC',
        brackets: [[54345, 0.14], [108680, 0.19], [132245, 0.24], [null, 0.2575]],
        basic_personal_amount: 18571
      },
      'Alberta': {
        code: 'AB',
        brackets: [[61200, 0.08], [154259, 0.10], [185111, 0.12], [246813, 0.13], [370220, 0.14], [null, 0.15]],
        basic_personal_amount: 22769
      }
    },
    province_aliases: {
      'ontario': 'Ontario', 'on': 'Ontario',
      'british columbia': 'British Columbia', 'bc': 'British Columbia',
      'quebec': 'Quebec', 'québec': 'Quebec', 'qc': 'Quebec',
      'alberta': 'Alberta', 'ab': 'Alberta'
    },
    pension: { ympe: 74600, basic_exemption: 3500, cpp_rate: 0.0595, qpp_rate: 0.064 },
    ei: { max_insurable: 68900, rate: 0.0163, quebec_rate: 0.0130 },
    qpip: { max_insurable: 103000, rate: 0.00494 }
  };

  /* ===================== CORE: presets (presets.py) ===================== */
  var PRESETS = {
    source_note: 'rough 2026 planning figures, not quotes: typical one-bedroom rent and a regular adult monthly transit pass',
    cities: {
      'Toronto': { province: 'Ontario', rent_per_month: 2450, transit_pass_per_month: 160 },
      'Waterloo': { province: 'Ontario', rent_per_month: 1900, transit_pass_per_month: 100 },
      'Ottawa': { province: 'Ontario', rent_per_month: 2050, transit_pass_per_month: 136 },
      'Vancouver': { province: 'British Columbia', rent_per_month: 2700, transit_pass_per_month: 110 },
      'Montreal': { province: 'Quebec', rent_per_month: 1750, transit_pass_per_month: 104 },
      'Calgary': { province: 'Alberta', rent_per_month: 1750, transit_pass_per_month: 118 }
    },
    aliases: {
      'toronto': 'Toronto', 'waterloo': 'Waterloo', 'ottawa': 'Ottawa',
      'vancouver': 'Vancouver', 'montreal': 'Montreal', 'calgary': 'Calgary',
      'montréal': 'Montreal'
    }
  };

  function findPreset(city) {
    if (typeof city !== 'string') return [null, null];
    var name = PRESETS.aliases[city.trim().toLowerCase()];
    if (name === undefined) return [null, null];
    return [name, PRESETS.cities[name]];
  }

  /* ===================== CORE: validation (model.py) ===================== */
  var ARRANGEMENTS = ['remote', 'hybrid', 'onsite'];
  var COMMUTE_MODES = ['transit', 'driving', 'none'];
  var OFFER_FIELDS = ['label', 'city', 'province', 'hourly_rate', 'hours_per_week',
    'annual_salary', 'term_weeks', 'arrangement', 'rent_per_month',
    'commute', 'other_monthly', 'moving_costs', 'lump_sums'];
  var COMMUTE_FIELDS = {
    transit: ['mode', 'transit_pass_per_month'],
    driving: ['mode', 'km_per_day', 'cost_per_km', 'parking_per_month', 'days_per_week'],
    none: ['mode']
  };
  var ALL_COMMUTE_FIELDS = ['mode', 'transit_pass_per_month', 'km_per_day', 'cost_per_km',
    'parking_per_month', 'days_per_week'];
  var DEFAULT_DRIVING_DAYS = { onsite: 5, hybrid: 3, remote: 0 };
  var MAX_AMOUNT = 100000000;

  function has(obj, key) { return Object.prototype.hasOwnProperty.call(obj, key); }
  function get(obj, key) { return has(obj, key) ? obj[key] : null; }
  function isObj(x) { return x !== null && typeof x === 'object' && !Array.isArray(x); }
  function isNumber(x) { return typeof x === 'number' && isFinite(x); }

  function fmtNum(x) {
    if (typeof x === 'boolean') return x ? 'true' : 'false';
    return String(x);
  }
  function describe(v) {
    if (v === null || v === undefined) return 'null';
    if (typeof v === 'boolean') return v ? 'true' : 'false';
    if (typeof v === 'string') return '"' + v + '"';
    if (Array.isArray(v)) return 'a list';
    if (typeof v === 'object') return 'an object';
    return fmtNum(v);
  }

  function Collector() { this.issues = []; }
  Collector.prototype.error = function (code, offer, field, message) {
    this.issues.push({ level: 'error', code: code, offer: offer, field: field, message: message });
  };
  Collector.prototype.warning = function (code, offer, field, message) {
    this.issues.push({ level: 'warning', code: code, offer: offer, field: field, message: message });
  };

  function money_(c, n, obj, key, path, required, positive) {
    if (!has(obj, key) || obj[key] === null || obj[key] === undefined) {
      if (required) c.error('E_MISSING', n, path, 'missing required field `' + path + '`.');
      return null;
    }
    var v = obj[key];
    if (!isNumber(v)) {
      c.error('E_NOT_NUMBER', n, path, '`' + path + '` must be a number, got ' + describe(v) + '.');
      return null;
    }
    if (v < 0) {
      c.error('E_NEGATIVE', n, path, '`' + path + '` cannot be negative, got ' + fmtNum(v) +
        '. Enter costs and pay as positive amounts.');
      return null;
    }
    if (positive && v === 0) {
      c.error('E_ZERO', n, path, '`' + path + '` must be greater than 0.');
      return null;
    }
    if (v > MAX_AMOUNT) {
      c.error('E_RANGE', n, path, '`' + path + '` is ' + fmtNum(v) + '; anything over ' + fmtNum(MAX_AMOUNT) +
        ' is treated as a typo.');
      return null;
    }
    return v;
  }

  function items(c, n, obj, key, allowTaxable) {
    var raw = get(obj, key);
    if (raw === null || raw === undefined) return [];
    if (!Array.isArray(raw)) {
      c.error('E_NOT_LIST', n, key, '`' + key + '` must be a list of {"name": ..., "amount": ...} items.');
      return [];
    }
    var out = [];
    raw.forEach(function (item, i) {
      var path = key + '[' + (i + 1) + ']';
      if (!isObj(item)) {
        c.error('E_NOT_OBJECT', n, path, '`' + path + '` must be an object like {"name": "phone", "amount": 50}.');
        return;
      }
      var name = get(item, 'name');
      if (typeof name !== 'string' || !name.trim()) {
        c.error('E_MISSING', n, path + '.name', 'missing required field `' + path + '.name` (a short description).');
        name = null;
      }
      var amount = money_(c, n, item, 'amount', path + '.amount', true, false);
      var allowed = allowTaxable ? ['name', 'amount', 'taxable'] : ['name', 'amount'];
      Object.keys(item).forEach(function (k) {
        if (allowed.indexOf(k) < 0 && k.charAt(0) !== '_') {
          c.warning('W_UNKNOWN_FIELD', n, path + '.' + k, 'unknown field `' + path + '.' + k + '` was ignored.');
        }
      });
      var taxable = true;
      if (allowTaxable && has(item, 'taxable')) {
        if (typeof item.taxable === 'boolean') taxable = item.taxable;
        else c.error('E_NOT_BOOL', n, path + '.taxable', '`' + path + '.taxable` must be true or false.');
      }
      if (name !== null && amount !== null) {
        var entry = { name: name.trim(), amount: amount };
        if (allowTaxable) entry.taxable = taxable;
        out.push(entry);
      }
    });
    return out;
  }

  function validateOffer(c, n, o, seen) {
    if (!isObj(o)) {
      c.error('E_NOT_OBJECT', n, '', 'offer ' + n + ' must be a JSON object.');
      return null;
    }
    var start = c.issues.length;

    Object.keys(o).forEach(function (k) {
      if (OFFER_FIELDS.indexOf(k) < 0 && k.charAt(0) !== '_') {
        c.warning('W_UNKNOWN_FIELD', n, k, 'unknown field `' + k + '` was ignored.');
      }
    });

    var label = get(o, 'label');
    if (typeof label !== 'string' || !label.trim()) {
      c.error('E_MISSING', n, 'label', 'missing required field `label` (e.g. "Employer - Role").');
      label = null;
    } else {
      label = label.trim();
      if (seen[label.toLowerCase()]) {
        c.error('E_DUPLICATE_LABEL', n, 'label', 'label "' + label + '" is used by more than one offer; labels must be unique.');
      }
      seen[label.toLowerCase()] = true;
    }

    var city = get(o, 'city');
    var preset = null;
    if (typeof city !== 'string' || !city.trim()) {
      c.error('E_MISSING', n, 'city', 'missing required field `city`.');
      city = null;
    } else {
      city = city.trim();
      var found = findPreset(city);
      preset = found[1];
      if (preset === null) {
        c.warning('W_NO_PRESET', n, 'city', 'no preset for city "' + city + '"; rent and transit must come from your file.');
      } else {
        city = found[0];
      }
    }

    var province = null, provinceSource = null;
    if (has(o, 'province') && o.province !== null) {
      var raw = o.province;
      var canon = typeof raw === 'string' ? TABLES.province_aliases[raw.trim().toLowerCase()] : undefined;
      if (canon === undefined) {
        c.error('E_PROVINCE', n, 'province', 'unsupported province ' + describe(raw) +
          '; use Ontario, British Columbia, Quebec, or Alberta.');
      } else {
        province = canon; provinceSource = 'user';
        if (preset !== null && preset.province !== canon) {
          c.warning('W_PROVINCE_MISMATCH', n, 'province', city + ' is in ' + preset.province +
            ' but province is ' + canon + '; tax uses ' + canon + '.');
        }
      }
    } else if (preset !== null) {
      province = preset.province; provinceSource = 'preset';
    } else {
      province = 'Ontario'; provinceSource = 'default';
    }

    var hasHourly = has(o, 'hourly_rate') || has(o, 'hours_per_week');
    var hasSalary = has(o, 'annual_salary');
    var payStyle = null, hourlyRate = null, hoursPerWeek = null, annualSalary = null;
    if (hasHourly && hasSalary) {
      c.error('E_BOTH_PAY', n, 'pay', 'give EITHER `hourly_rate` + `hours_per_week` OR `annual_salary`, not both.');
    } else if (!hasHourly && !hasSalary) {
      c.error('E_NO_PAY', n, 'pay', 'no pay given; add `hourly_rate` + `hours_per_week` OR `annual_salary`.');
    } else if (hasHourly) {
      payStyle = 'hourly';
      hourlyRate = money_(c, n, o, 'hourly_rate', 'hourly_rate', true, true);
      hoursPerWeek = money_(c, n, o, 'hours_per_week', 'hours_per_week', true, true);
      if (hoursPerWeek !== null && hoursPerWeek > 80) {
        c.error('E_RANGE', n, 'hours_per_week', '`hours_per_week` is ' + fmtNum(hoursPerWeek) + '; it must be 80 or less.');
        hoursPerWeek = null;
      } else if (hoursPerWeek !== null && hoursPerWeek > 60) {
        c.warning('W_LONG_HOURS', n, 'hours_per_week', '`hours_per_week` is ' + fmtNum(hoursPerWeek) + '; double-check that is right.');
      }
    } else {
      payStyle = 'salary';
      annualSalary = money_(c, n, o, 'annual_salary', 'annual_salary', true, true);
    }

    var termWeeks = null;
    var tw = get(o, 'term_weeks');
    if (tw === null) {
      c.error('E_MISSING', n, 'term_weeks', 'missing required field `term_weeks` (co-op terms are usually 16).');
    } else if (!isNumber(tw) || !Number.isInteger(tw) || tw <= 0) {
      c.error('E_TERM', n, 'term_weeks', '`term_weeks` must be a positive whole number of weeks, got ' + describe(tw) + '.');
    } else {
      termWeeks = tw;
    }

    var arrangement = get(o, 'arrangement');
    if (arrangement === null) {
      c.error('E_MISSING', n, 'arrangement', 'missing required field `arrangement` (remote, hybrid, or onsite).');
    } else if (ARRANGEMENTS.indexOf(arrangement) < 0) {
      c.error('E_ARRANGEMENT', n, 'arrangement', '`arrangement` must be remote, hybrid, or onsite, got ' + describe(arrangement) + '.');
      arrangement = null;
    }

    var rent = null, rentSource = null;
    if (has(o, 'rent_per_month') && o.rent_per_month !== null) {
      rent = money_(c, n, o, 'rent_per_month', 'rent_per_month', true, false);
      rentSource = 'user';
    } else if (preset !== null) {
      rent = preset.rent_per_month; rentSource = 'preset';
    } else {
      c.error('E_MISSING', n, 'rent_per_month', 'missing `rent_per_month` and there is no city preset to start from.');
    }

    var commute = get(o, 'commute');
    var mode = null;
    var transit = 0, transitSource = 'n/a';
    var km = 0, costKm = 0, parking = 0, days = 0;
    var parkingSource = 'n/a', daysSource = 'n/a';
    if (commute === null) {
      if (arrangement === 'remote') {
        mode = 'none';
      } else {
        c.error('E_MISSING', n, 'commute', 'missing `commute`; add {"mode": "transit"}, {"mode": "driving", ...}, or {"mode": "none"} if remote.');
      }
    } else if (!isObj(commute)) {
      c.error('E_NOT_OBJECT', n, 'commute', '`commute` must be an object like {"mode": "transit"}.');
    } else {
      mode = get(commute, 'mode');
      if (COMMUTE_MODES.indexOf(mode) < 0) {
        c.error('E_COMMUTE_MODE', n, 'commute.mode', '`commute.mode` must be transit, driving, or none, got ' + describe(mode) + '.');
        mode = null;
      }
      Object.keys(commute).forEach(function (k) {
        if (k.charAt(0) === '_') return;
        if (ALL_COMMUTE_FIELDS.indexOf(k) < 0) {
          c.warning('W_UNKNOWN_FIELD', n, 'commute.' + k, 'unknown field `commute.' + k + '` was ignored.');
        } else if (mode !== null && COMMUTE_FIELDS[mode].indexOf(k) < 0) {
          c.warning('W_IGNORED_FIELD', n, 'commute.' + k, '`commute.' + k + '` is ignored when the mode is ' + mode + '.');
        }
      });
    }

    if (mode === 'none' && arrangement === 'onsite') {
      c.error('E_ONSITE_NO_COMMUTE', n, 'commute.mode',
        'an onsite job needs a commute; use transit or driving (walking or cycling: transit with transit_pass_per_month 0).');
    } else if (mode === 'none' && arrangement === 'hybrid') {
      c.warning('W_HYBRID_NO_COMMUTE', n, 'commute.mode',
        'hybrid job with no commute cost; add one unless you really walk or cycle.');
    } else if ((mode === 'transit' || mode === 'driving') && arrangement === 'remote') {
      c.warning('W_REMOTE_COMMUTE', n, 'commute.mode',
        'remote job with a ' + mode + ' cost; it is counted, but check you need it.');
    }

    if (mode === 'transit') {
      if (get(commute, 'transit_pass_per_month') !== null) {
        transit = money_(c, n, commute, 'transit_pass_per_month', 'commute.transit_pass_per_month', true, false);
        transitSource = 'user';
      } else if (preset !== null) {
        transit = preset.transit_pass_per_month; transitSource = 'preset';
      } else {
        c.error('E_MISSING', n, 'commute.transit_pass_per_month',
          'missing `commute.transit_pass_per_month` and there is no city preset to start from.');
      }
    } else if (mode === 'driving') {
      km = money_(c, n, commute, 'km_per_day', 'commute.km_per_day', true, false);
      costKm = money_(c, n, commute, 'cost_per_km', 'commute.cost_per_km', true, false);
      if (get(commute, 'parking_per_month') !== null) {
        parking = money_(c, n, commute, 'parking_per_month', 'commute.parking_per_month', true, false);
        parkingSource = 'user';
      } else {
        parking = 0; parkingSource = 'assumed';
        c.warning('W_ASSUMED', n, 'commute.parking_per_month',
          'no `commute.parking_per_month`; assuming free parking (0).');
      }
      if (get(commute, 'days_per_week') !== null) {
        var d = commute.days_per_week;
        if (!isNumber(d) || d <= 0 || d > 7) {
          c.error('E_RANGE', n, 'commute.days_per_week',
            '`commute.days_per_week` must be more than 0 and at most 7, got ' + describe(d) + '.');
          days = null;
        } else {
          days = d; daysSource = 'user';
        }
      } else if (arrangement !== null) {
        days = DEFAULT_DRIVING_DAYS[arrangement]; daysSource = 'assumed';
        c.warning('W_ASSUMED', n, 'commute.days_per_week',
          'no `commute.days_per_week`; assuming ' + fmtNum(days) +
          ' driving days a week for a ' + arrangement + ' job.');
      }
    }

    var other = items(c, n, o, 'other_monthly', false);
    var moving = items(c, n, o, 'moving_costs', false);
    var lumps = items(c, n, o, 'lump_sums', true);

    for (var i = start; i < c.issues.length; i++) {
      if (c.issues[i].level === 'error') return null;
    }
    return {
      label: label, city: city, province: province, province_source: provinceSource,
      pay_style: payStyle, hourly_rate: hourlyRate, hours_per_week: hoursPerWeek,
      annual_salary: annualSalary, term_weeks: termWeeks, arrangement: arrangement,
      rent_per_month: rent, rent_source: rentSource, commute_mode: mode,
      transit_pass_per_month: transit, transit_source: transitSource,
      km_per_day: km, cost_per_km: costKm, parking_per_month: parking,
      parking_source: parkingSource, days_per_week: days, days_source: daysSource,
      other_monthly: other, moving_costs: moving, lump_sums: lumps
    };
  }

  function validate(data) {
    var c = new Collector();
    var rawOffers;
    if (Array.isArray(data)) {
      rawOffers = data;
    } else if (isObj(data)) {
      Object.keys(data).forEach(function (k) {
        if (k !== 'offers' && k.charAt(0) !== '_') {
          c.warning('W_UNKNOWN_FIELD', null, k, 'unknown top-level field `' + k + '` was ignored.');
        }
      });
      rawOffers = get(data, 'offers');
    } else {
      rawOffers = null;
    }
    if (!Array.isArray(rawOffers)) {
      c.error('E_NO_OFFERS', null, 'offers', 'the file must be an object with an `offers` list (run `init` for an example).');
      return { offers: [], issues: c.issues };
    }
    if (rawOffers.length === 0) {
      c.error('E_NO_OFFERS', null, 'offers', 'the `offers` list is empty; add at least one offer.');
      return { offers: [], issues: c.issues };
    }
    var offers = [];
    var seen = {};
    rawOffers.forEach(function (o, i) {
      var norm = validateOffer(c, i + 1, o, seen);
      if (norm !== null) offers.push(norm);
    });
    return { offers: offers, issues: c.issues };
  }

  /* ===================== CORE: math (calc.py) ===================== */
  var TIE_THRESHOLD = 25;
  var RENT_SHIFT = 200;
  var WPM = TABLES.weeks_per_month;
  var WPY = TABLES.weeks_per_year;

  function round2(x) { return Math.floor(x * 100 + 0.5) / 100; }

  function addUp(values) {
    var total = 0;
    for (var i = 0; i < values.length; i++) total = total + values[i];
    return total;
  }

  function bracketTax(income, brackets) {
    var tax = 0, lower = 0;
    for (var i = 0; i < brackets.length; i++) {
      var limit = brackets[i][0], rate = brackets[i][1];
      if (income <= lower) break;
      var top = limit === null ? income : Math.min(income, limit);
      tax = tax + (top - lower) * rate;
      if (limit === null) break;
      lower = limit;
    }
    return tax;
  }

  function marginalRate(income, brackets) {
    for (var i = 0; i < brackets.length; i++) {
      var limit = brackets[i][0];
      if (limit === null || income < limit) return brackets[i][1];
    }
    return brackets[brackets.length - 1][1];
  }

  function annualIncomeTax(income, province) {
    var fb = TABLES.federal.brackets;
    var federal = bracketTax(income, fb) - TABLES.federal.basic_personal_amount * fb[0][1];
    if (federal < 0) federal = 0;
    if (province === 'Quebec') federal = federal * (1 - TABLES.quebec_abatement);
    var p = TABLES.provinces[province];
    var pb = p.brackets;
    var provincial = bracketTax(income, pb) - p.basic_personal_amount * pb[0][1];
    if (provincial < 0) provincial = 0;
    return [federal, provincial];
  }

  function combinedMarginalRate(income, province) {
    var fed = marginalRate(income, TABLES.federal.brackets);
    if (province === 'Quebec') fed = fed * (1 - TABLES.quebec_abatement);
    return fed + marginalRate(income, TABLES.provinces[province].brackets);
  }

  function grossForTerm(o) {
    if (o.pay_style === 'hourly') return o.hourly_rate * o.hours_per_week * o.term_weeks;
    return o.annual_salary * o.term_weeks / WPY;
  }

  function commutePerMonth(o) {
    if (o.commute_mode === 'transit') return o.transit_pass_per_month;
    if (o.commute_mode === 'driving') {
      return o.km_per_day * o.cost_per_km * o.days_per_week * WPM + o.parking_per_month;
    }
    return 0;
  }

  function amounts(list, onlyTaxable) {
    var out = [];
    list.forEach(function (i) { if (!onlyTaxable || i.taxable) out.push(i.amount); });
    return out;
  }

  function computeOffer(o) {
    var weeks = o.term_weeks;
    var province = o.province;
    var months = weeks / WPM;
    var yearShare = weeks / WPY;

    var gross = grossForTerm(o);
    var annualised = gross * WPY / weeks;
    var t = annualIncomeTax(annualised, province);
    var fedAnnual = t[0], provAnnual = t[1];
    var federalTax = fedAnnual * yearShare;
    var provincialTax = provAnnual * yearShare;

    var quebec = province === 'Quebec';
    var P = TABLES.pension;
    var pensionRate = quebec ? P.qpp_rate : P.cpp_rate;
    var pensionMax = (P.ympe - P.basic_exemption) * pensionRate;
    var pensionable = Math.min(gross, P.ympe) - P.basic_exemption * yearShare;
    if (pensionable < 0) pensionable = 0;
    var pension = Math.min(pensionable * pensionRate, pensionMax);

    var eiRate = quebec ? TABLES.ei.quebec_rate : TABLES.ei.rate;
    var ei = Math.min(gross, TABLES.ei.max_insurable) * eiRate;
    var qpip = quebec ? Math.min(gross, TABLES.qpip.max_insurable) * TABLES.qpip.rate : 0;

    var deductions = addUp([federalTax, provincialTax, pension, ei, qpip]);
    var net = gross - deductions;

    var commute = commutePerMonth(o);
    var other = addUp(amounts(o.other_monthly, false));
    var livingMonth = addUp([o.rent_per_month, commute, other]);
    var livingTerm = livingMonth * months;
    var moving = addUp(amounts(o.moving_costs, false));

    var lumpGross = addUp(amounts(o.lump_sums, false));
    var lumpTaxable = addUp(amounts(o.lump_sums, true));
    var lumpTax = 0;
    if (lumpTaxable > 0) {
      var t2 = annualIncomeTax(annualised + lumpTaxable, province);
      lumpTax = (t2[0] + t2[1]) - (fedAnnual + provAnnual);
    }
    var lumpNet = lumpGross - lumpTax;

    var takehomeTerm = net - livingTerm - moving + lumpNet;
    var annualTax = fedAnnual + provAnnual;

    return {
      label: o.label, city: o.city, province: province, arrangement: o.arrangement,
      pay_style: o.pay_style, term_weeks: weeks, term_months: months,
      gross_term: gross, gross_month: gross / months, annualised_income: annualised,
      federal_tax: federalTax, provincial_tax: provincialTax,
      pension: pension, pension_name: quebec ? 'QPP' : 'CPP', ei: ei, qpip: qpip,
      deductions_total: deductions,
      effective_deduction_rate: gross > 0 ? deductions / gross : 0,
      average_income_tax_rate: annualised > 0 ? annualTax / annualised : 0,
      marginal_tax_rate: combinedMarginalRate(annualised, province),
      net_term: net, net_month: net / months,
      rent_month: o.rent_per_month, commute_month: commute, other_month: other,
      living_month: livingMonth, living_term: livingTerm,
      moving_total: moving, moving_per_month: moving / months,
      lump_gross: lumpGross, lump_tax: lumpTax, lump_net: lumpNet,
      takehome_term: takehomeTerm, takehome_month: takehomeTerm / months,
      takehome_week: takehomeTerm / weeks,
      sources: {
        province: o.province_source, rent: o.rent_source, transit: o.transit_source,
        parking: o.parking_source, driving_days: o.days_source
      }
    };
  }

  function copy(o) { var c = {}; Object.keys(o).forEach(function (k) { c[k] = o[k]; }); return c; }
  function withPay(o, value) {
    var c = copy(o);
    if (c.pay_style === 'hourly') c.hourly_rate = value; else c.annual_salary = value;
    return c;
  }
  function withRent(o, rent) { var c = copy(o); c.rent_per_month = rent; return c; }
  function currentPay(o) { return o.pay_style === 'hourly' ? o.hourly_rate : o.annual_salary; }

  function money(x) {
    var r = round2(x);
    var sign = r < 0 ? '-' : '';
    var parts = Math.abs(r).toFixed(2).split('.');
    var whole = parts[0];
    var groups = [];
    while (whole.length > 3) {
      groups.unshift(whole.slice(-3));
      whole = whole.slice(0, -3);
    }
    groups.unshift(whole);
    return sign + '$' + groups.join(',') + '.' + parts[1];
  }

  function rank(results) {
    var order = results.map(function (_, i) { return i; });
    order.sort(function (a, b) { return results[b].takehome_month - results[a].takehome_month; });
    var best = results[order[0]];
    var rows = order.map(function (i, pos) {
      var gap = best.takehome_month - results[i].takehome_month;
      return {
        rank: pos + 1, index: i, label: results[i].label,
        gap_to_best_month: gap,
        about_tied: pos > 0 && round2(gap) <= TIE_THRESHOLD
      };
    });
    rows.forEach(function (row) { row.verdict = verdict(row, rows, results); });
    return rows;
  }

  function verdict(row, rows, results) {
    if (rows.length === 1) {
      return 'Only offer: ' + money(results[row.index].takehome_month) + '/month take-home.';
    }
    var best = rows[0];
    if (row.rank === 1) {
      var tied = rows.slice(1).filter(function (r) { return r.about_tied; }).map(function (r) { return r.label; });
      if (tied.length) {
        return 'Highest monthly take-home, but about tied with ' + tied.join(', ') +
          ' (within ' + money(TIE_THRESHOLD) + '/month): treat them as equal on money ' +
          'and decide on the job itself.';
      }
      var nxt = rows[1];
      return 'Best monthly take-home: ' + money(nxt.gap_to_best_month) + '/month more than ' + nxt.label + '.';
    }
    if (row.about_tied) {
      return 'About tied with ' + best.label + ': only ' + money(row.gap_to_best_month) +
        "/month behind, which is inside the estimate's margin.";
    }
    return money(row.gap_to_best_month) + '/month less take-home than ' + best.label + '.';
  }

  function breakeven(targetOffer, offer, iterations) {
    if (iterations === undefined) iterations = 100;
    var target = computeOffer(targetOffer).takehome_month;
    var now = currentPay(offer);
    var nowMonth = computeOffer(offer).takehome_month;
    function f(pay) { return computeOffer(withPay(offer, pay)).takehome_month; }
    var result = {
      target_label: targetOffer.label, label: offer.label, pay_style: offer.pay_style,
      current_pay: now, current_takehome_month: nowMonth, target_takehome_month: target,
      required_pay: null, change: null, change_pct: null, reachable: true
    };
    var required;
    if (f(0) >= target) {
      required = 0;
    } else {
      var lo = 0;
      var hi = now > 0 ? now * 2 : 1;
      var steps = 0;
      while (f(hi) < target && steps < 40) { hi = hi * 2; steps = steps + 1; }
      if (f(hi) < target) { result.reachable = false; return result; }
      for (var k = 0; k < iterations; k++) {
        var mid = (lo + hi) / 2;
        if (f(mid) < target) lo = mid; else hi = mid;
      }
      required = hi;
    }
    result.required_pay = required;
    result.change = required - now;
    result.change_pct = now > 0 ? (required - now) / now : null;
    return result;
  }

  function breakevenText(be) {
    var unit = be.pay_style === 'hourly' ? '/hour' : '/year';
    if (!be.reachable) {
      return 'No realistic ' + (be.pay_style === 'hourly' ? 'hourly rate' : 'salary') +
        ' lets ' + be.label + ' match ' + be.target_label + '.';
    }
    var need = Math.ceil(be.required_pay * 100) / 100;
    if (be.required_pay === 0) {
      return be.label + ' matches ' + be.target_label + ' even at zero pay (its costs are that much lower).';
    }
    var pct = '';
    if (be.change_pct !== null) {
      var tenths = Math.floor(Math.abs(be.change_pct) * 1000 + 0.5) / 10;
      pct = ' (' + (be.change >= 0 ? '+' : '-') + tenths.toFixed(1) + '%)';
    }
    if (be.change > 0) {
      return be.label + ' would need ' + money(need) + unit + ' instead of ' +
        money(be.current_pay) + unit + pct + ' to match the monthly take-home of ' +
        be.target_label + '.';
    }
    return be.label + ' already matches ' + be.target_label + '; it could pay as little as ' +
      money(need) + unit + ' instead of ' + money(be.current_pay) + unit + pct +
      ' and still keep up.';
  }

  function sensitivity(offers, results, index, shift) {
    if (shift === undefined) shift = RENT_SHIFT;
    var offer = offers[index];
    var out = { shift: shift, base: results[index].takehome_month };
    [['rent_up', shift], ['rent_down', -shift]].forEach(function (kd) {
      var newRent = offer.rent_per_month + kd[1];
      if (newRent < 0) newRent = 0;
      var r = computeOffer(withRent(offer, newRent));
      var trial = results.slice();
      trial[index] = r;
      var ranked = rank(trial);
      var newRank = ranked.filter(function (row) { return row.index === index; })[0].rank;
      out[kd[0]] = { rent: newRent, takehome_month: r.takehome_month, rank: newRank };
    });
    return out;
  }

  function compare(offers) {
    var results = offers.map(computeOffer);
    var ranking = rank(results);
    var bestIndex = ranking[0].index;
    var baseRank = {};
    ranking.forEach(function (row) { baseRank[row.index] = row.rank; });
    var sens = offers.map(function (_, i) {
      var s = sensitivity(offers, results, i);
      s.label = results[i].label;
      s.rank = baseRank[i];
      s.fragile = s.rent_up.rank !== s.rank || s.rent_down.rank !== s.rank;
      return s;
    });
    var pairs = ranking.slice(1).map(function (row) {
      var be = breakeven(offers[bestIndex], offers[row.index]);
      be.text = breakevenText(be);
      return be;
    });
    return { results: results, ranking: ranking, breakeven: pairs, sensitivity: sens };
  }

  var CORE = {
    TABLES: TABLES, PRESETS: PRESETS, TIE_THRESHOLD: TIE_THRESHOLD, RENT_SHIFT: RENT_SHIFT,
    findPreset: findPreset, validate: validate, round2: round2, money: money,
    computeOffer: computeOffer, rank: rank, breakeven: breakeven, breakevenText: breakevenText,
    sensitivity: sensitivity, compare: compare, withPay: withPay
  };

  if (typeof module !== 'undefined' && module.exports) module.exports = CORE;
  root.CoopCore = CORE;
  if (typeof document === 'undefined') return;

  /* ===================== UI (browser only) ===================== */
  var MAX_OFFERS = 4;
  var EXAMPLE = [
    {
      label: 'Toronto data analyst (synthetic)', city: 'Toronto', province: 'Ontario', pay_style: 'hourly',
      hourly_rate: '28', hours_per_week: '37.5', annual_salary: '', term_weeks: '16', arrangement: 'hybrid',
      rent: '', rent_preset: true, mode: 'transit', transit: '', transit_preset: true,
      km: '', cost_km: '', parking: '', days: '',
      other: 'phone plan, 45\ngroceries, 380', moving: 'moving van, 350', lumps: 'signing bonus, 1000'
    },
    {
      label: 'Waterloo QA developer (synthetic)', city: 'Waterloo', province: 'Ontario', pay_style: 'hourly',
      hourly_rate: '24', hours_per_week: '40', annual_salary: '', term_weeks: '16', arrangement: 'onsite',
      rent: '1150', rent_preset: false, mode: 'transit', transit: '', transit_preset: true,
      km: '', cost_km: '', parking: '', days: '',
      other: 'phone plan, 45\ngroceries, 380', moving: '', lumps: ''
    }
  ];
  var SOURCE_WORDS = {
    user: 'you supplied', preset: 'city preset (estimate)', 'default': 'default (Ontario)',
    assumed: 'assumed (not supplied)', 'n/a': 'not used'
  };

  var $ = function (sel, el) { return (el || document).querySelector(sel); };
  var offersEl, tmpl, nextId = 1;

  function blankState() {
    return {
      label: '', city: '', province: '', pay_style: 'hourly', hourly_rate: '', hours_per_week: '',
      annual_salary: '', term_weeks: '16', arrangement: 'onsite', rent: '', rent_preset: false,
      mode: 'transit', transit: '', transit_preset: false, km: '', cost_km: '', parking: '', days: '',
      other: '', moving: '', lumps: ''
    };
  }

  function numOrNull(v) {
    v = String(v).trim();
    if (v === '') return null;
    var n = Number(v.replace(/[$,\s]/g, ''));
    return isFinite(n) ? n : v;
  }

  /* "name, amount" per line; lump sums may add ", untaxed". */
  function parseItems(text, allowTaxable) {
    var out = [];
    String(text).split('\n').forEach(function (line) {
      line = line.trim();
      if (!line) return;
      var parts = line.split(',').map(function (p) { return p.trim(); });
      var item = {};
      if (allowTaxable && parts.length >= 3 && /^untaxed$/i.test(parts[parts.length - 1])) {
        item.taxable = false;
        parts.pop();
      }
      var amount = parts.length > 1 ? numOrNull(parts.pop()) : null;
      item.name = parts.join(', ');
      item.amount = amount;
      out.push(item);
    });
    return out;
  }

  function readCard(card) {
    var f = function (name) { return card.querySelector('[data-f="' + name + '"]'); };
    var raw = {
      label: f('label').value, city: f('city').value
    };
    if (f('province').value) raw.province = f('province').value;
    if (card.querySelector('[data-f="pay_style"]:checked').value === 'hourly') {
      raw.hourly_rate = numOrNull(f('hourly_rate').value);
      raw.hours_per_week = numOrNull(f('hours_per_week').value);
    } else {
      raw.annual_salary = numOrNull(f('annual_salary').value);
    }
    raw.term_weeks = numOrNull(f('term_weeks').value);
    raw.arrangement = f('arrangement').value;
    var rent = f('rent');
    if (!(rent.dataset.preset === '1')) raw.rent_per_month = numOrNull(rent.value);
    var mode = f('mode').value;
    var commute = { mode: mode };
    if (mode === 'transit') {
      var tr = f('transit');
      if (!(tr.dataset.preset === '1')) commute.transit_pass_per_month = numOrNull(tr.value);
    } else if (mode === 'driving') {
      commute.km_per_day = numOrNull(f('km').value);
      commute.cost_per_km = numOrNull(f('cost_km').value);
      commute.parking_per_month = numOrNull(f('parking').value);
      commute.days_per_week = numOrNull(f('days').value);
    }
    raw.commute = commute;
    raw.other_monthly = parseItems(f('other').value, false);
    raw.moving_costs = parseItems(f('moving').value, false);
    raw.lump_sums = parseItems(f('lumps').value, true);
    return raw;
  }

  function setPresetFlag(input, on) {
    input.dataset.preset = on ? '1' : '';
    var tag = input.parentNode.querySelector('.src');
    if (tag) tag.textContent = on ? 'preset estimate' : (input.value.trim() ? 'your value' : '');
  }

  function applyPreset(card, cityName) {
    var p = PRESETS.cities[cityName];
    var f = function (name) { return card.querySelector('[data-f="' + name + '"]'); };
    f('city').value = cityName;
    f('province').value = p.province;
    f('rent').value = String(p.rent_per_month);
    setPresetFlag(f('rent'), true);
    f('transit').value = String(p.transit_pass_per_month);
    setPresetFlag(f('transit'), true);
    update();
  }

  function syncVisibility(card) {
    var hourly = card.querySelector('[data-f="pay_style"]:checked').value === 'hourly';
    card.querySelector('.pay-hourly').hidden = !hourly;
    card.querySelector('.pay-salary').hidden = hourly;
    var mode = card.querySelector('[data-f="mode"]').value;
    card.querySelector('.c-transit').hidden = mode !== 'transit';
    card.querySelector('.c-driving').hidden = mode !== 'driving';
  }

  function addCard(state) {
    if (offersEl.children.length >= MAX_OFFERS) return null;
    state = state || blankState();
    var id = nextId++;
    var card = tmpl.content.firstElementChild.cloneNode(true);
    card.querySelectorAll('[data-id]').forEach(function (el) {
      if (el.id) el.id = el.id + '-' + id;
      if (el.htmlFor) el.htmlFor = el.htmlFor + '-' + id;
      if (el.name) el.name = el.name + '-' + id;
      var d = el.getAttribute('aria-describedby');
      if (d) el.setAttribute('aria-describedby', d.split(' ').map(function (x) { return x + '-' + id; }).join(' '));
    });
    var f = function (name) { return card.querySelector('[data-f="' + name + '"]'); };
    f('label').value = state.label;
    f('city').value = state.city;
    f('province').value = state.province;
    card.querySelector('[data-f="pay_style"][value="' + state.pay_style + '"]').checked = true;
    f('hourly_rate').value = state.hourly_rate;
    f('hours_per_week').value = state.hours_per_week;
    f('annual_salary').value = state.annual_salary;
    f('term_weeks').value = state.term_weeks;
    f('arrangement').value = state.arrangement;
    f('mode').value = state.mode;
    ['km', 'cost_km', 'parking', 'days', 'other', 'moving', 'lumps'].forEach(function (k) {
      f(k).value = state[k];
    });
    var preset = findPreset(state.city)[1];
    f('rent').value = state.rent_preset && preset ? String(preset.rent_per_month) : state.rent;
    f('transit').value = state.transit_preset && preset ? String(preset.transit_pass_per_month) : state.transit;
    setPresetFlag(f('rent'), state.rent_preset && !!preset);
    setPresetFlag(f('transit'), state.transit_preset && !!preset);

    card.querySelectorAll('[data-preset-city]').forEach(function (btn) {
      btn.addEventListener('click', function () { applyPreset(card, btn.dataset.presetCity); });
    });
    card.querySelector('.remove').addEventListener('click', function () {
      card.remove();
      renumber();
      update();
      $('#add-offer').focus();
    });
    card.addEventListener('input', function (ev) {
      var t = ev.target;
      if (t.dataset.f === 'rent' || t.dataset.f === 'transit') setPresetFlag(t, false);
      if (t.dataset.f === 'city') {
        // a different city means the old preset numbers no longer apply
        ['rent', 'transit'].forEach(function (k) { if (f(k).dataset.preset === '1') { f(k).value = ''; setPresetFlag(f(k), false); } });
      }
      syncVisibility(card);
      update();
    });
    card.addEventListener('change', function () { syncVisibility(card); update(); });
    offersEl.appendChild(card);
    syncVisibility(card);
    renumber();
    return card;
  }

  function renumber() {
    Array.prototype.forEach.call(offersEl.children, function (card, i) {
      card.querySelector('.offer-num').textContent = String(i + 1);
      card.querySelector('.remove').setAttribute('aria-label', 'Remove offer ' + (i + 1));
      card.querySelector('.presets').setAttribute('aria-label', 'Offer ' + (i + 1) + ': fill rent and transit estimates for a city');
    });
    $('#add-offer').disabled = offersEl.children.length >= MAX_OFFERS;
    $('#offer-count').textContent = offersEl.children.length + ' of ' + MAX_OFFERS + ' offers';
  }

  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function pct(x) { return round2(x * 100).toFixed(1) + '%'; }

  var LINES = [
    ['gross_term', 'Gross pay, whole term', 'money'],
    ['federal_tax', 'Federal income tax (est.)', 'money'],
    ['provincial_tax', 'Provincial income tax (est.)', 'money'],
    ['pension', 'CPP / QPP (est.)', 'money'],
    ['ei', 'EI (est.)', 'money'],
    ['qpip', 'QPIP (Quebec only, est.)', 'money'],
    ['deductions_total', 'Total deductions', 'money'],
    ['effective_deduction_rate', 'Effective deduction rate', 'pct'],
    ['net_term', 'Net pay, whole term', 'money'],
    ['rent_month', 'Rent per month', 'money'],
    ['commute_month', 'Commute per month', 'money'],
    ['other_month', 'Other costs per month', 'money'],
    ['living_month', 'Living costs per month', 'money'],
    ['living_term', 'Living costs, whole term', 'money'],
    ['moving_total', 'One-time moving costs', 'money'],
    ['moving_per_month', 'Moving, spread per month', 'money'],
    ['lump_gross', 'Lump sums before tax', 'money'],
    ['lump_tax', 'Tax on lump sums (est.)', 'money'],
    ['lump_net', 'Lump sums after tax', 'money'],
    ['takehome_term', 'Take-home, whole term', 'money'],
    ['takehome_month', 'Take-home per month', 'money'],
    ['takehome_week', 'Take-home per week', 'money']
  ];

  var lastOffers = [];

  function renderIssues(issues) {
    var box = $('#issues');
    if (!issues.length) { box.hidden = true; box.innerHTML = ''; box.dataset.key = ''; return; }
    var key = JSON.stringify(issues);
    if (box.dataset.key === key) return;
    box.dataset.key = key;
    var errors = issues.filter(function (i) { return i.level === 'error'; });
    var warns = issues.filter(function (i) { return i.level === 'warning'; });
    var html = '<h3>' + errors.length + ' problem' + (errors.length === 1 ? '' : 's') + ' to fix, ' +
      warns.length + ' warning' + (warns.length === 1 ? '' : 's') + '</h3><ol>';
    errors.concat(warns).forEach(function (i) {
      html += '<li class="' + i.level + '"><strong>' + (i.level === 'error' ? 'Error' : 'Warning') +
        '</strong> ' + esc(i.code) + (i.offer ? ' (offer ' + i.offer + (i.field ? ', ' + esc(i.field) : '') + ')' : '') +
        ': ' + esc(i.message) + '</li>';
    });
    box.innerHTML = html + '</ol>';
    box.hidden = false;
  }

  /* Map a validation field path to the demo input it came from. */
  var FIELD_INPUT = {
    label: 'label', city: 'city', province: 'province', pay: 'hourly_rate', hourly_rate: 'hourly_rate',
    hours_per_week: 'hours_per_week', annual_salary: 'annual_salary', term_weeks: 'term_weeks',
    arrangement: 'arrangement', rent_per_month: 'rent', commute: 'mode', 'commute.mode': 'mode',
    'commute.transit_pass_per_month': 'transit', 'commute.km_per_day': 'km', 'commute.cost_per_km': 'cost_km',
    'commute.parking_per_month': 'parking', 'commute.days_per_week': 'days',
    other_monthly: 'other', moving_costs: 'moving', lump_sums: 'lumps'
  };

  function markInvalid(issues) {
    var cards = offersEl.children;
    Array.prototype.forEach.call(offersEl.querySelectorAll('[aria-invalid]'), function (el) {
      el.removeAttribute('aria-invalid');
    });
    issues.forEach(function (i) {
      if (i.level !== 'error' || !i.offer || !cards[i.offer - 1]) return;
      var key = FIELD_INPUT[i.field] || FIELD_INPUT[String(i.field).split('[')[0]];
      if (!key) return;
      var el = cards[i.offer - 1].querySelector('[data-f="' + key + '"]');
      if (el) el.setAttribute('aria-invalid', 'true');
    });
  }

  function setSummary(text) {
    var el = $('#summary');
    if (el.textContent !== text) el.textContent = text;
  }

  function update() {
    var raws = Array.prototype.map.call(offersEl.children, readCard);
    var out = $('#results');
    var blank = raws.every(function (r) {
      return !String(r.label).trim() && !String(r.city).trim() && r.hourly_rate == null && r.annual_salary == null;
    });
    if (!raws.length || blank) {
      renderIssues([]);
      markInvalid([]);
      setSummary('');
      out.innerHTML = '<p>Fill in an offer, or load the synthetic example, to see a comparison.</p>';
      lastOffers = [];
      renderBreakevenControls();
      return;
    }
    var v = validate(raws);
    renderIssues(v.issues);
    markInvalid(v.issues);
    var bad = v.issues.some(function (i) { return i.level === 'error'; });
    if (bad || !v.offers.length) {
      setSummary('Comparison paused: fix the problems listed above.');
      out.innerHTML = '<p>Fix the problems listed above and the comparison will appear here.</p>';
      lastOffers = [];
      renderBreakevenControls();
      return;
    }
    lastOffers = v.offers;
    var cmp = compare(v.offers);
    var top = cmp.ranking[0];
    setSummary(cmp.ranking.length === 1 ? 'One offer: ' + money(cmp.results[0].takehome_month) + ' a month take-home (estimate).'
      : 'Best monthly take-home: ' + top.label + ', ' + money(cmp.results[top.index].takehome_month) +
        (cmp.ranking[1].about_tied ? ' (about tied with ' + cmp.ranking[1].label + ').' : '.'));
    out.innerHTML = renderResults(cmp);
    renderBreakevenControls();
  }

  function renderResults(cmp) {
    var res = cmp.results;
    var h = '';
    // ranking
    h += '<h3 id="rank-h">Ranking by monthly take-home</h3>';
    h += '<div class="scroll" role="region" aria-labelledby="rank-h" tabindex="0"><table><thead><tr><th scope="col">Rank</th><th scope="col">Offer</th>' +
      '<th scope="col">Per month</th><th scope="col">Whole term</th><th scope="col">Per week</th>' +
      '<th scope="col">Gap to best / month</th><th scope="col">Verdict</th></tr></thead><tbody>';
    cmp.ranking.forEach(function (row) {
      var r = res[row.index];
      h += '<tr><td>' + row.rank + (row.about_tied ? ' <span class="tied">about tied</span>' : '') +
        '</td><th scope="row">' + esc(r.label) + '</th><td>' + money(r.takehome_month) + '</td><td>' +
        money(r.takehome_term) + '</td><td>' + money(r.takehome_week) + '</td><td>' +
        money(row.gap_to_best_month) + '</td><td class="txt">' + esc(row.verdict) + '</td></tr>';
    });
    h += '</tbody></table></div>';

    // bar chart (values repeated in the ranking table above)
    var maxAbs = 0;
    res.forEach(function (r) { maxAbs = Math.max(maxAbs, Math.abs(r.takehome_month)); });
    h += '<figure class="chart"><figcaption id="chart-cap">Monthly take-home, highest first (estimates). ' +
      'The same numbers are in the ranking table above.</figcaption><ul class="bars">';
    cmp.ranking.forEach(function (row) {
      var r = res[row.index];
      var w = maxAbs > 0 ? Math.round(Math.abs(r.takehome_month) / maxAbs * 100) : 0;
      var neg = r.takehome_month < 0;
      h += '<li><span class="bar-label">' + esc(r.label) + '</span><span class="bar-track">' +
        '<span class="bar' + (neg ? ' neg' : '') + '" style="width:' + w + '%"></span></span>' +
        '<span class="bar-value">' + money(r.takehome_month) + (neg ? ' (costs exceed pay)' : '') + '</span></li>';
    });
    h += '</ul></figure>';

    // side by side
    h += '<h3 id="side-h">Side by side, every line</h3>';
    h += '<div class="scroll" role="region" aria-labelledby="side-h" tabindex="0"><table><thead><tr><th scope="col">Line</th>';
    res.forEach(function (r) { h += '<th scope="col">' + esc(r.label) + '</th>'; });
    h += '</tr></thead><tbody>';
    LINES.forEach(function (line) {
      var total = line[0].indexOf('takehome') === 0;
      h += '<tr' + (total ? ' class="total"' : '') + '><th scope="row">' + line[1] + '</th>';
      res.forEach(function (r) {
        h += '<td>' + (line[2] === 'pct' ? pct(r[line[0]]) : money(r[line[0]])) + '</td>';
      });
      h += '</tr>';
    });
    h += '</tbody></table></div>';

    // provenance
    h += '<h3>Where each number came from</h3><ul class="prov">';
    res.forEach(function (r) {
      var s = r.sources;
      var parts = ['province: ' + SOURCE_WORDS[s.province], 'rent: ' + SOURCE_WORDS[s.rent]];
      if (s.transit !== 'n/a') parts.push('transit pass: ' + SOURCE_WORDS[s.transit]);
      if (s.parking !== 'n/a') parts.push('parking: ' + SOURCE_WORDS[s.parking]);
      if (s.driving_days !== 'n/a') parts.push('driving days: ' + SOURCE_WORDS[s.driving_days]);
      h += '<li><strong>' + esc(r.label) + '</strong>: ' + esc(parts.join('; ')) + '</li>';
    });
    h += '</ul>';

    // break-even vs best
    if (cmp.breakeven.length) {
      h += '<h3>Break-even against the best offer</h3><ul>';
      cmp.breakeven.forEach(function (be) { h += '<li>' + esc(be.text) + '</li>'; });
      h += '</ul>';
    }

    // sensitivity
    h += '<h3 id="sens-h">How fragile is this? Rent ' + money(RENT_SHIFT) + '/month higher or lower</h3>';
    h += '<div class="scroll" role="region" aria-labelledby="sens-h" tabindex="0"><table><thead><tr><th scope="col">Offer</th><th scope="col">Rent &minus;$200</th>' +
      '<th scope="col">As entered</th><th scope="col">Rent +$200</th><th scope="col">Rank changes?</th></tr></thead><tbody>';
    cmp.sensitivity.forEach(function (s) {
      h += '<tr><th scope="row">' + esc(s.label) + '</th><td>' + money(s.rent_down.takehome_month) + '</td><td>' +
        money(s.base) + '</td><td>' + money(s.rent_up.takehome_month) + '</td><td>' +
        (s.fragile ? 'yes, the ranking flips' : 'no') + '</td></tr>';
    });
    h += '</tbody></table></div>';
    return h;
  }

  function renderBreakevenControls() {
    var a = $('#be-target'), b = $('#be-adjust');
    var keepA = a.value, keepB = b.value;
    var opts = lastOffers.map(function (o, i) {
      return '<option value="' + i + '">' + esc(o.label) + '</option>';
    }).join('');
    a.innerHTML = opts; b.innerHTML = opts;
    if (keepA && +keepA < lastOffers.length) a.value = keepA;
    if (keepB && +keepB < lastOffers.length) b.value = keepB;
    else if (lastOffers.length > 1) b.value = a.value === '0' ? '1' : '0';
    var ok = lastOffers.length >= 2;
    a.disabled = !ok; b.disabled = !ok; $('#be-run').disabled = !ok;
    if (!ok) $('#be-out').textContent = 'Enter at least two valid offers to use the break-even calculator.';
  }

  function runBreakeven() {
    var i = +$('#be-target').value, j = +$('#be-adjust').value;
    var out = $('#be-out');
    if (i === j) { out.textContent = 'Pick two different offers.'; return; }
    var be = breakeven(lastOffers[i], lastOffers[j]);
    var text = breakevenText(be);
    if (be.reachable && be.required_pay) {
      var check = computeOffer(withPay(lastOffers[j], be.required_pay)).takehome_month;
      text += ' Check: at that pay its monthly take-home is ' + money(check) + ', against ' +
        money(be.target_takehome_month) + ' for ' + be.target_label + '. Costs stay fixed; only pay moves.';
    }
    out.textContent = text;
  }

  function loadExample() {
    while (offersEl.firstChild) offersEl.removeChild(offersEl.firstChild);
    EXAMPLE.forEach(function (s) { addCard(s); });
    update();
    $('#example-note').hidden = false;
    $('#results-h').focus();
  }

  function init() {
    offersEl = $('#offers');
    tmpl = $('#offer-template');
    $('#add-offer').addEventListener('click', function () {
      var card = addCard();
      update();
      if (card) card.querySelector('[data-f="label"]').focus();
    });
    $('#load-example').addEventListener('click', loadExample);
    $('#be-run').addEventListener('click', runBreakeven);
    addCard();
    update();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})(typeof globalThis !== 'undefined' ? globalThis : this);
