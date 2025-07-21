#[derive(Debug, PartialEq, Eq, Clone, Copy)]
pub enum Answer {
    U8(u8),
    U16(u16),
}

impl From<u8> for Answer {
    fn from(value: u8) -> Self {
        Answer::U8(value)
    }
}

impl From<u16> for Answer {
    fn from(value: u16) -> Self {
        Answer::U16(value)
    }
}

impl PartialEq<u8> for Answer {
    fn eq(&self, other: &u8) -> bool {
        *self == Answer::from(*other)
    }
}

impl PartialEq<u16> for Answer {
    fn eq(&self, other: &u16) -> bool {
        *self == Answer::from(*other)
    }
}

impl std::fmt::Display for Answer {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            Answer::U8(value) => write!(f, "{value}"),
            Answer::U16(value) => write!(f, "{value}"),
        }
    }
}
