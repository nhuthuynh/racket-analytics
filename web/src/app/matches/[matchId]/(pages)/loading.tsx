// The match pages' loading state (C-30): the same as the list's. Lives in the (pages) route group
// so that the stats routes beside it have no loading boundary and can answer 404 (G03-06).
export { default } from '../../(list)/loading';
