use aoc::answer::Answer;
use aoc::map::Map;
use itertools::Itertools;
use log::{debug, log_enabled};
use std::cell::OnceCell;
use std::collections::HashMap;
use std::collections::HashSet;
use std::fmt;
use std::process::ExitCode;

fn main() -> ExitCode {
    aoc::run::run(p1, p2)
}

#[must_use]
pub fn p1(input: &str) -> Answer {
    let (start_point, map) = process_input(input);

    let mut visited = HashSet::new();
    let mut direction = Direction::North;
    let mut cur = start_point;

    loop {
        let (x, y) = cur;
        let (dir_visited, ends_in_obstruction) =
            process_direction(&map, x, y, direction, |(_, _, s)| s.is_obstruction());
        cur = *dir_visited.last().unwrap();
        visited.extend(dir_visited);

        if ends_in_obstruction {
            direction = direction.turn_right();
        } else {
            break;
        }
    }

    Answer::U16(visited.len().try_into().unwrap())
}

#[must_use]
pub fn p2(input: &str) -> Answer {
    let (start_point, map) = process_input(input);

    let mut route = Vec::new();
    let mut direction = Direction::North;
    let mut cur = start_point;

    loop {
        let (x, y) = cur;
        let (dir_visited, ends_in_obstruction) =
            process_direction(&map, x, y, direction, |(_, _, s)| s.is_obstruction());
        cur = *dir_visited.last().unwrap();
        route.extend(dir_visited.into_iter().map(|(x, y)| (x, y, direction)));

        if ends_in_obstruction {
            direction = direction.turn_right();
        } else {
            break;
        }
    }

    // TODO: Move this into fold itself
    let mut new_obstruction_locations = HashSet::new();
    route.iter().tuple_windows().fold(
        LoopDataSoFar::new(),
        |mut data_so_far, (v_for_turn, v_for_obstruction)| {
            if v_for_turn.0 != v_for_obstruction.0 && v_for_turn.1 != v_for_obstruction.1 {
                // Already a turn -> no new obstruction to place
                assert_ne!(v_for_turn.2, v_for_obstruction.2);
            } else if data_so_far
                .visited_points
                .contains(&(v_for_obstruction.0, v_for_obstruction.1))
            {
                // Already been here -> can't place obstruction here
            } else if detect_loop(
                &map,
                &data_so_far,
                *v_for_turn,
                (v_for_obstruction.0, v_for_obstruction.1),
            ) {
                debug!(
                    "Loop with obstruction at: {:?}",
                    (v_for_obstruction.0, v_for_obstruction.1)
                );
                new_obstruction_locations.insert((v_for_obstruction.0, v_for_obstruction.1));
            }

            data_so_far.push(*v_for_turn);
            data_so_far
        },
    );

    Answer::U16(new_obstruction_locations.len().try_into().unwrap())
}

struct LoopDataSoFar {
    pub route: Vec<(usize, usize, Direction)>,
    pub visited: HashSet<(usize, usize, Direction)>,
    pub visited_points: HashSet<(usize, usize)>,
}

impl LoopDataSoFar {
    pub fn new() -> Self {
        Self {
            route: Vec::new(),
            visited: HashSet::new(),
            visited_points: HashSet::new(),
        }
    }

    pub fn push(&mut self, (x, y, direction): (usize, usize, Direction)) {
        self.route.push((x, y, direction));
        self.visited.insert((x, y, direction));
        self.visited_points.insert((x, y));
    }
}

fn detect_loop(
    map: &Map<MapSymbol>,
    data_so_far: &LoopDataSoFar,
    route_point_before_new_obstruction: (usize, usize, Direction),
    new_obstruction: (usize, usize),
) -> bool {
    let mut visited = data_so_far.visited.clone();
    let (cur_x, cur_y, dir) = route_point_before_new_obstruction;
    let mut cur = (cur_x, cur_y);
    let mut direction = dir.turn_right();

    loop {
        let (x, y) = cur;
        let (dir_visited, ends_in_obstruction) =
            process_direction(map, x, y, direction, |(x, y, s)| {
                (x, y) == new_obstruction || s.is_obstruction()
            });
        cur = *dir_visited.last().unwrap();

        if !ends_in_obstruction {
            // Can't be a loop as it goes out of the map
            return false;
        }

        //dir_visited.pop();
        let new_visits: HashSet<_> = dir_visited
            .into_iter()
            .map(|(x, y)| (x, y, direction))
            .collect();
        if !visited.is_disjoint(&new_visits) {
            log_loop_path(
                map,
                &data_so_far.route,
                &visited,
                &new_visits,
                new_obstruction,
            );
            return true;
        }

        visited.extend(new_visits);
        direction = direction.turn_right();
    }
}

fn log_loop_path(
    map: &Map<MapSymbol>,
    route: &[(usize, usize, Direction)],
    visited: &HashSet<(usize, usize, Direction)>,
    new_visits: &HashSet<(usize, usize, Direction)>,
    new_obstruction: (usize, usize),
) {
    if !log_enabled!(log::Level::Debug) {
        return;
    }

    let route_points: HashMap<(usize, usize), char> = route
        .iter()
        .copied()
        .tuple_windows()
        .map(|(v1, v2)| {
            let (x1, y1, dir1) = v1;
            let (x2, y2, dir2) = v2;
            let sym = {
                if x1 == x2 && y1 == y2 {
                    assert_ne!(dir1, dir2);
                    '+'
                } else if dir2 == Direction::North || dir2 == Direction::South {
                    'I'
                } else {
                    '='
                }
            };
            ((x2, y2), sym)
        })
        .collect();

    let new_points: HashMap<(usize, usize), char> = new_visits
        .union(visited)
        .sorted_by_key(|(x, y, _)| (*x, *y))
        .chunk_by(|(x, y, _)| (*x, *y))
        .into_iter()
        .map(|(pos, chunk)| {
            let dirs = chunk.map(|(_, _, dir)| dir).copied().collect::<Vec<_>>();
            let sym = {
                match dirs.len() {
                    1 => {
                        if dirs[0] == Direction::North || dirs[0] == Direction::South {
                            '|'
                        } else {
                            '-'
                        }
                    }
                    2 => {
                        assert_ne!(dirs[0], dirs[1]);
                        '+'
                    }
                    3 => {
                        assert_ne!(dirs[0], dirs[1]);
                        assert_ne!(dirs[0], dirs[2]);
                        assert_ne!(dirs[1], dirs[2]);
                        'X'
                    }
                    _ => unreachable!(),
                }
            };
            (pos, sym)
        })
        .collect();

    let start = route.first().unwrap();

    let mut msg: String = String::new();
    for y in 0..map.height() {
        let mut msg_line = String::new();
        for x in 0..map.width() {
            let (x, y) = (x, y);
            if (x, y) == (start.0, start.1) {
                msg_line.push('S');
            } else if (x, y) == new_obstruction {
                msg_line.push('O');
            } else if let Some(sym) = route_points.get(&(x, y)) {
                msg_line.push(*sym);
            } else if let Some(sym) = new_points.get(&(x, y)) {
                msg_line.push(*sym);
            } else {
                msg_line.push_str(&map.get(x, y).unwrap().to_string());
            }
        }
        msg_line.push('\n');
        msg.push_str(&msg_line);
    }

    log::debug!("{msg}");
}

fn process_direction(
    map: &Map<MapSymbol>,
    x: usize,
    y: usize,
    direction: Direction,
    is_obstruction: impl Fn((usize, usize, MapSymbol)) -> bool,
) -> (Vec<(usize, usize)>, bool) {
    match direction {
        Direction::North => process_points(
            map.iter_from_point_to_north(x, y)
                .enumerate()
                .map(|(i, s)| (x, y - i, *s)),
            is_obstruction,
        ),
        Direction::South => process_points(
            map.iter_from_point_to_south(x, y)
                .enumerate()
                .map(|(i, s)| (x, y + i, *s)),
            is_obstruction,
        ),
        Direction::East => process_points(
            map.iter_from_point_to_east(x, y)
                .enumerate()
                .map(|(i, s)| (x + i, y, *s)),
            is_obstruction,
        ),
        Direction::West => process_points(
            map.iter_from_point_to_west(x, y)
                .enumerate()
                .map(|(i, s)| (x - i, y, *s)),
            is_obstruction,
        ),
    }
}

fn process_points(
    iter: impl Iterator<Item = (usize, usize, MapSymbol)>,
    is_obstruction: impl Fn((usize, usize, MapSymbol)) -> bool,
) -> (Vec<(usize, usize)>, bool) {
    let (dir_visited, ends_in_obstruction) = iter
        .map(|(x, y, s)| (x, y, is_obstruction((x, y, s))))
        .map(Some)
        .chain(std::iter::once(None))
        .tuple_windows()
        .map(|(v1, v2)| {
            assert!(v1.is_some());
            let (x, y, _) = v1.unwrap();
            let followed_by_obstruction = match v2 {
                None => Some(false),
                Some((_, _, is_obstruction)) => {
                    if is_obstruction {
                        Some(true)
                    } else {
                        None
                    }
                }
            };
            (x, y, followed_by_obstruction)
        })
        .take_while_inclusive(|(_, _, followed_by_obstruction)| followed_by_obstruction.is_none())
        .fold(
            (Vec::new(), None),
            |(mut dir_visited, ends_in_obstruction), (x, y, followed_by_obstruction)| {
                assert!(ends_in_obstruction.is_none());
                dir_visited.push((x, y));
                (dir_visited, followed_by_obstruction)
            },
        );

    assert!(ends_in_obstruction.is_some());
    (dir_visited, ends_in_obstruction.unwrap())
}

fn process_input(input: &str) -> ((usize, usize), Map<MapSymbol>) {
    let start_point = OnceCell::new();
    let map: Map<MapSymbol> = {
        let start_point = &start_point;
        input
            .split('\n')
            .enumerate()
            .map(|(y, line)| {
                line.bytes()
                    .enumerate()
                    .map(move |(x, c)| {
                        if c == b'^' {
                            start_point.set((x, y)).unwrap();
                            b'.'
                        } else {
                            c
                        }
                    })
                    .map(MapSymbol::new)
            })
            .collect()
    };
    (start_point.into_inner().unwrap(), map)
}

#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug)]
enum Direction {
    North,
    South,
    East,
    West,
}

impl Direction {
    fn turn_right(self) -> Self {
        use Direction::{East, North, South, West};
        match self {
            North => East,
            East => South,
            South => West,
            West => North,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq)]
struct MapSymbol(bool);

impl MapSymbol {
    fn new(c: u8) -> Self {
        match c {
            b'#' => MapSymbol(true),
            b'.' => MapSymbol(false),
            _ => unreachable!(),
        }
    }

    fn is_obstruction(self) -> bool {
        self.0
    }
}

impl fmt::Display for MapSymbol {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        if self.0 {
            write!(f, "#")
        } else {
            write!(f, ".")
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use aoc::test_utils::prepare_example_input;

    const EXAMPLE_INPUT: &str = r"
....#.....
.........#
..........
..#.......
.......#..
..........
.#..^.....
........#.
#.........
......#...";

    #[test]
    fn test_p1() {
        let input = prepare_example_input(EXAMPLE_INPUT);
        assert_eq!(p1(input), 41u16);
    }

    #[test]
    fn test_p2() {
        let _ = simple_logger::init_with_env();
        let input = prepare_example_input(EXAMPLE_INPUT);
        assert_eq!(p2(input), 6u16);
    }
}
