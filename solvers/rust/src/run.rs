use itertools::Itertools;
use log::Level;
use std::env;
use std::io::Read;
use std::process::ExitCode;

use crate::answer::Answer;

enum Part {
    P1,
    P2,
}

fn process_args() -> Part {
    let (verbosity_arg, part_arg) = env::args().skip(1).collect_tuple().unwrap();
    let verbosity: u32 = verbosity_arg.parse().unwrap();
    let level = match verbosity {
        0 => Level::Warn,
        1 => Level::Info,
        2 => Level::Debug,
        _ => panic!("invalid verbosity level: {verbosity}"),
    };
    simple_logger::init_with_level(level).unwrap();

    match part_arg.as_str() {
        "1" => Part::P1,
        "2" => Part::P2,
        _ => panic!("unknown part: {part_arg}"),
    }
}

pub fn run(p1: fn(&str) -> Answer, p2: fn(&str) -> Answer) -> ExitCode {
    let part = process_args();

    let input_str = {
        let mut input_str = String::new();
        std::io::stdin().read_to_string(&mut input_str).unwrap();
        input_str
    };

    let input = input_str.trim_end();
    let answer = match part {
        Part::P1 => p1(input),
        Part::P2 => p2(input),
    };

    println!("{answer}");
    ExitCode::from(0)
}
