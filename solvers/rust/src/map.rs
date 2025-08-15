pub struct Map<Data> {
    data: Vec<Vec<Data>>,
}

impl<Data> Map<Data> {
    #[must_use]
    pub fn get(&self, x: usize, y: usize) -> Option<&Data> {
        self.data.get(y)?.get(x)
    }

    pub fn iter_from_point_to_north(&self, x: usize, y: usize) -> impl Iterator<Item = &Data> {
        MapYIterator::<Data, true>::new(self, x, y)
    }

    pub fn iter_from_point_to_south(&self, x: usize, y: usize) -> impl Iterator<Item = &Data> {
        MapYIterator::<Data, false>::new(self, x, y)
    }

    pub fn iter_from_point_to_east(&self, x: usize, y: usize) -> impl Iterator<Item = &Data> {
        self.data[y].iter().skip(x)
    }

    pub fn iter_from_point_to_west(&self, x: usize, y: usize) -> impl Iterator<Item = &Data> {
        self.data[y].iter().rev().skip((self.width() - 1) - x)
    }

    #[must_use]
    pub fn width(&self) -> usize {
        self.data[0].len()
    }

    #[must_use]
    pub fn height(&self) -> usize {
        self.data.len()
    }
}

impl<Data, IterX> FromIterator<IterX> for Map<Data>
where
    IterX: Iterator<Item = Data>,
{
    fn from_iter<IterY>(iter_y: IterY) -> Self
    where
        IterY: IntoIterator<Item = IterX>,
    {
        let mut data = Vec::new();
        let mut width = None;
        for iter_x in iter_y {
            let row_data: Vec<_> = iter_x.into_iter().collect();
            let row_width = row_data.len();
            match width {
                Some(w) => assert_eq!(w, row_width),
                None => width = Some(row_width),
            }
            data.push(row_data);
        }
        Self { data }
    }
}

pub(crate) struct MapYIterator<'a, Data, const TO_NORTH: bool> {
    map: &'a Map<Data>,
    x: usize,
    y: Option<usize>,
}

impl<'a, Data, const TO_NORTH: bool> MapYIterator<'a, Data, TO_NORTH> {
    pub fn new(map: &'a Map<Data>, x: usize, y: usize) -> Self {
        Self { map, x, y: Some(y) }
    }
}

impl<'a, Data> Iterator for MapYIterator<'a, Data, true> {
    type Item = &'a Data;

    fn next(&mut self) -> Option<Self::Item> {
        match self.y {
            None => None,
            Some(y) => {
                let result = self.map.get(self.x, y);
                if y == 0 {
                    self.y = None;
                } else {
                    self.y = Some(y - 1);
                }
                result
            }
        }
    }
}

impl<'a, Data> Iterator for MapYIterator<'a, Data, false> {
    type Item = &'a Data;

    fn next(&mut self) -> Option<Self::Item> {
        match self.y {
            None => None,
            Some(y) => {
                let result = self.map.get(self.x, y);
                if y == self.map.height() - 1 {
                    self.y = None;
                } else {
                    self.y = Some(y + 1);
                }
                result
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_map() {
        let map: Map<u8> = vec![vec![1u8, 2, 3], vec![4, 5, 6], vec![7, 8, 9]]
            .into_iter()
            .map(std::iter::IntoIterator::into_iter)
            .collect();
        assert_eq!(map.get(0, 0), Some(&1));
        assert_eq!(map.get(1, 0), Some(&2));
        assert_eq!(map.get(2, 0), Some(&3));
        assert_eq!(map.get(0, 1), Some(&4));
        assert_eq!(map.get(1, 1), Some(&5));
        assert_eq!(map.get(2, 1), Some(&6));
        assert_eq!(map.get(0, 2), Some(&7));
        assert_eq!(map.get(1, 2), Some(&8));
        assert_eq!(map.get(2, 2), Some(&9));

        assert_eq!(
            map.iter_from_point_to_north(1, 1).collect::<Vec<_>>(),
            vec![&5, &2]
        );
        assert_eq!(
            map.iter_from_point_to_east(1, 1).collect::<Vec<_>>(),
            vec![&5, &6]
        );
        assert_eq!(
            map.iter_from_point_to_south(1, 1).collect::<Vec<_>>(),
            vec![&5, &8]
        );
        assert_eq!(
            map.iter_from_point_to_west(1, 1).collect::<Vec<_>>(),
            vec![&5, &4]
        );
    }
}
