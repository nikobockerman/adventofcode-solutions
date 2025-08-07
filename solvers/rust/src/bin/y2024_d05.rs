#![warn(
    clippy::complexity,
    clippy::correctness,
    clippy::pedantic,
    clippy::perf,
    clippy::style,
    clippy::suspicious
)]
use aoc::answer::Answer;
use itertools::Itertools;
use std::collections::HashMap;
use std::collections::HashSet;
use std::process::ExitCode;

fn main() -> ExitCode {
    aoc::run::run(p1, p2)
}

pub fn p1(input: &str) -> Answer {
    let parts = load_parts(input);
    let dependencies = construct_dependencies_map(parts.0);

    let result: u16 = parts
        .1
        .filter(|pages| contains_correctly_ordered_update_pages(&dependencies, pages))
        .map(|pages| get_middle_value(&pages))
        .map(u16::from)
        .sum();

    result.into()
}

pub fn p2(input: &str) -> Answer {
    let parts = load_parts(input);
    let dependencies = construct_dependencies_map(parts.0);

    let result: u16 = parts
        .1
        .filter(|pages| !contains_correctly_ordered_update_pages(&dependencies, pages))
        .map(|mut pages| {
            pages.sort_by(|a, b| {
                if let Some(a_deps) = dependencies.get(a)
                    && a_deps.contains(b)
                {
                    return std::cmp::Ordering::Less;
                }
                if let Some(b_deps) = dependencies.get(b)
                    && b_deps.contains(a)
                {
                    return std::cmp::Ordering::Greater;
                }
                std::cmp::Ordering::Equal
            });
            pages
        })
        .map(|pages| get_middle_value(&pages))
        .map(u16::from)
        .sum();
    result.into()
}

fn get_middle_value(pages: &[u8]) -> u8 {
    let size = pages.len();
    assert_eq!(size % 2, 1, "Expected odd number of pages");
    *pages.get(size / 2).unwrap()
}

fn contains_correctly_ordered_update_pages(
    dependencies: &HashMap<u8, HashSet<u8>>,
    pages: &[u8],
) -> bool {
    let mut pages_before: HashSet<u8> = HashSet::new();
    pages.iter().all(|page| {
        if let Some(deps) = dependencies.get(page)
            && !pages_before.is_disjoint(deps)
        {
            return false;
        }
        pages_before.insert(*page);
        true
    })
}

fn construct_dependencies_map<I>(page_ordering_rules: I) -> HashMap<u8, HashSet<u8>>
where
    I: Iterator<Item = (u8, u8)>,
{
    page_ordering_rules
        .chunk_by(|(dependee, _)| *dependee)
        .into_iter()
        .map(|(dependee, dependency_rules)| {
            (dependee, dependency_rules.map(|(_, dependency)| dependency))
        })
        .fold(HashMap::new(), |mut map, (dependee, dependents)| {
            map.entry(dependee).or_default().extend(dependents);
            map
        })
}

fn load_parts(
    input: &str,
) -> (
    impl Iterator<Item = (u8, u8)>,
    impl Iterator<Item = Vec<u8>>,
) {
    let mut parts = input.split("\n\n").map(|s| s.split('\n'));
    (
        load_page_ordering_rules(parts.next().unwrap()),
        load_update_page_numbers(parts.next().unwrap()),
    )
}

fn load_page_ordering_rules<'a, I>(page_ordering_rules: I) -> impl Iterator<Item = (u8, u8)> + 'a
where
    I: Iterator<Item = &'a str> + 'a,
{
    page_ordering_rules.map(|s| {
        let parts = s
            .split('|')
            .map(|s| s.parse::<u8>().unwrap())
            .collect::<Vec<_>>();
        (parts[0], parts[1])
    })
}

fn load_update_page_numbers<'a, I>(update_page_numbers: I) -> impl Iterator<Item = Vec<u8>> + 'a
where
    I: Iterator<Item = &'a str> + 'a,
{
    update_page_numbers.map(|s| {
        s.split(',')
            .map(|s| s.parse::<u8>().unwrap())
            .collect::<Vec<_>>()
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use aoc::test_utils::prepare_example_input;

    const EXAMPLE_INPUT: &str = r"
47|53
97|13
97|61
97|47
75|29
61|13
75|53
29|13
97|29
53|29
61|53
97|53
61|29
47|13
75|47
97|75
47|61
75|61
47|29
75|13
53|13

75,47,61,53,29
97,61,53,29,13
75,29,13
75,97,47,61,53
61,13,29
97,13,75,29,47";

    #[test]
    fn test_p1() {
        let input = prepare_example_input(EXAMPLE_INPUT);
        assert_eq!(p1(input), 143u16);
    }

    #[test]
    fn test_p2() {
        let input = prepare_example_input(EXAMPLE_INPUT);
        assert_eq!(p2(input), 123u16);
    }
}
