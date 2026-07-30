//! Small static set of high-Hispanic Texas ZIP codes.
//!
//! If a lead ZIP is unknown / not in this set, do **not** award the
//! "No Spanish version" points; set `zip_unknown: true` in signals instead.

use std::collections::HashSet;
use std::sync::OnceLock;

/// Texas ZIPs with high Hispanic/Latino share (curated, not exhaustive).
/// Sources: ACS high-share metros/border/RGV — checked-in static set only.
const HIGH_HISPANIC_ZIPS: &[&str] = &[
    // El Paso
    "79901", "79902", "79903", "79905", "79907", "79915", "79922", "79924", "79925",
    "79927", "79928", "79930", "79932", "79934", "79935", "79936", "79938",
    // Laredo
    "78040", "78041", "78043", "78045", "78046",
    // McAllen / Edinburg / Mission (RGV)
    "78501", "78503", "78504", "78516", "78537", "78539", "78541", "78542", "78557",
    "78572", "78573", "78574", "78577", "78589", "78596",
    // Brownsville / Harlingen
    "78520", "78521", "78526", "78550", "78552",
    // Corpus Christi (select)
    "78405", "78407", "78415", "78416",
    // San Antonio (high-Hispanic tracts)
    "78207", "78210", "78211", "78214", "78221", "78223", "78224", "78225", "78227",
    "78228", "78237", "78242", "78250", "78251",
    // Houston (select high-Hispanic)
    "77011", "77012", "77017", "77023", "77029", "77033", "77037", "77076", "77087",
    "77093", "77502", "77506", "77547",
    // Dallas (select)
    "75211", "75212", "75216", "75217", "75224", "75227", "75232", "75233", "75241",
    // Fort Worth (select)
    "76104", "76105", "76106", "76110", "76115", "76119",
    // Austin (select East/South)
    "78702", "78721", "78723", "78724", "78741", "78744", "78745", "78753",
];

fn set() -> &'static HashSet<&'static str> {
    static SET: OnceLock<HashSet<&'static str>> = OnceLock::new();
    SET.get_or_init(|| HIGH_HISPANIC_ZIPS.iter().copied().collect())
}

/// Returns `(is_high_hispanic, zip_unknown)`.
///
/// - Empty/None ZIP → not high, zip_unknown = true
/// - ZIP present but not in set → not high, zip_unknown = false
/// - ZIP in set → high, zip_unknown = false
pub fn zip_hispanic_flags(zip: Option<&str>) -> (bool, bool) {
    let Some(raw) = zip.map(str::trim).filter(|s| !s.is_empty()) else {
        return (false, true);
    };
    // Normalize to 5-digit when possible (ZIP+4 → first 5).
    let five = if raw.len() >= 5 { &raw[..5] } else { raw };
    if !five.chars().all(|c| c.is_ascii_digit()) {
        return (false, true);
    }
    let high = set().contains(five);
    (high, false)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn el_paso_is_high() {
        let (high, unknown) = zip_hispanic_flags(Some("79901"));
        assert!(high);
        assert!(!unknown);
    }

    #[test]
    fn unknown_zip_flag() {
        let (high, unknown) = zip_hispanic_flags(None);
        assert!(!high);
        assert!(unknown);
    }

    #[test]
    fn non_list_zip_not_unknown() {
        let (high, unknown) = zip_hispanic_flags(Some("78624"));
        assert!(!high);
        assert!(!unknown);
    }
}
