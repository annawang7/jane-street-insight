open Base

type t =
  { board : Filled_square.t option array array
  ; height : int
  ; width : int
  }

let create ~height ~width =
  { board = Array.make_matrix ~dimx:width ~dimy:height None; height; width }
;;

let get t { Point.col; row } = t.board.(col).(row)
let set t { Point.col; row } value = t.board.(col).(row) <- value

let mark_squares_that_are_sweepable t =
  (* TODO: at the end of this function the all filled_squares that are
     part of completed squares (anything that is in a single color
     square of 4 parts which includes combined groups) should be in
     sweeper state [To_sweep] and all other squares should be
     [Unmarked] *)
  for col = 0 to (t.width-2) do 
    for row = 0 to (t.height-2) do 
      let square = get t { col; row } in
      let squareRight = get t { col=col+1; row } in
      let squareAbove = get t { col; row=row+1} in
      let squareRightAbove = get t { col=col+1; row=row+1} in
      let all_exist = 
      match square, squareRight, squareAbove, squareRightAbove with
      | Some _, Some _, Some _, Some _ -> true
      | _, _, _, _ -> false in

      if (all_exist)
      then
        let square = Option.value_exn(square) in
        let squareRight = Option.value_exn(squareRight) in
        let squareAbove = Option.value_exn(squareAbove) in
        let squareRightAbove = Option.value_exn(squareRightAbove) in
        if Color.equal square.color squareRight.color && 
          Color.equal square.color squareAbove.color &&
          Color.equal square.color squareRightAbove.color
        then (
          square.sweeper_state <- To_sweep;
          squareRight.sweeper_state <- To_sweep;
          squareAbove.sweeper_state <- To_sweep;
          squareRightAbove.sweeper_state <- To_sweep
        )
    done
  done
;;

let remove_squares t =
  (* TODO: remove any squares marked as [Swept] from the board.
     Gravity should be applied appropriately.

     At the end of this function, we should call
     [mark_squares_that_are_sweepable] so that we ensure that we leave
     the board in a valid state.  *)
  ignore (mark_squares_that_are_sweepable t)
;;

let is_empty t point =
  match get t point with
  | None -> true
  | Some _ -> false
;;

let rec last_valid_row t col row =
  if row >= t.height
  then t.height
  else 
  match (is_empty t { col; row }) with
  | true -> row
  | false -> last_valid_row t col (row+1)

let add_piece t ~(moving_piece: Moving_piece.t) ~col =
  (* TODO: insert the moving piece into the board, applying gravity
     appropriately. Make sure to leave the board in a valid state. *)
  let col1_last_row = last_valid_row t col 0 in
  let col2_last_row = last_valid_row t (col+1) 0 in
  if ( col1_last_row >= t.height || col2_last_row >= t.height )
  then false
  else ( 
    set t { Point.col=col ; row=col1_last_row+1} (Some moving_piece.top_left);
    set t { Point.col=col+1 ; row=col2_last_row+1} (Some moving_piece.top_right);
    set t { Point.col=col ; row=col1_last_row  } (Some moving_piece.bottom_left);
    set t { Point.col=col+1 ; row=col2_last_row } (Some moving_piece.bottom_right);
    true
  )
;;

(* Tests *)
let is_filled_with_color t ~row ~col color = 
  match get t { Point. row; col} with
  | None -> false
  | Some square -> Color.equal color square.color
;;

let is_marked t ~row ~col = 
  match get t { Point. row; col} with
  | None -> false
  | Some square ->
    Filled_square.Sweeper_state.equal
      square.Filled_square.sweeper_state
      Filled_square.Sweeper_state.To_sweep
;;

let test_piece = 
  { Moving_piece. top_left = Filled_square.create (Color.Orange)
  ; top_right = Filled_square.create (Color.White)
  ; bottom_left = Filled_square.create (Color.White)
  ; bottom_right = Filled_square.create (Color.White)
  }
;;

let%test "Testing Add_piece add one..." = 
  let t = create ~height:4 ~width:4 in
  add_piece t ~moving_piece:test_piece ~col:0
  && is_filled_with_color t ~row:0 ~col:0 Color.White
  && is_filled_with_color t ~row:0 ~col:1 Color.White
  && is_filled_with_color t ~row:1 ~col:0 Color.Orange
  && is_filled_with_color t ~row:1 ~col:1 Color.White
;;

let%test "Testing Add_piece add many..." =
  let t = create ~height:4 ~width:4 in
  (add_piece t ~moving_piece:test_piece ~col:0)
  && (add_piece t ~moving_piece:test_piece ~col:0)
  && (not (add_piece t ~moving_piece:test_piece ~col:0))
;;

let test_removable_piece = 
  { Moving_piece. top_left = Filled_square.create (Color.White)
  ; top_right = Filled_square.create (Color.White)
  ; bottom_left = Filled_square.create (Color.White)
  ; bottom_right = Filled_square.create (Color.White)
  }
;;

let%test "Testing mark_squares_that_are_sweepable..." =
  let t = create ~height:4 ~width:4 in
  assert (add_piece  t ~moving_piece:test_removable_piece ~col:0);
  assert (add_piece  t ~moving_piece:test_piece ~col:0);
  mark_squares_that_are_sweepable t;
  is_marked t ~row:0 ~col:0 
  && is_marked t ~row:0 ~col:1
  && is_marked t ~row:1 ~col:0
  && is_marked t ~row:1 ~col:1
  && is_marked t ~row:2 ~col:0
  && is_marked t ~row:2 ~col:1
  && not (is_marked t ~row:3 ~col:0)
  && not (is_marked t ~row:3 ~col:1)
;;

let sweep_board t = 
  Array.iter t.board
    ~f:(fun row ->
        Array.iter row ~f:(fun square -> 
            Option.iter square
              ~f:(fun square -> ignore (Filled_square.sweep square))))
;;

let%test "Testing Remove_squares..." =
  let t = create ~height:4 ~width:4 in
  assert (add_piece  t ~moving_piece:test_removable_piece ~col:0);
  assert (add_piece  t ~moving_piece:test_piece ~col:0);
  mark_squares_that_are_sweepable t;
  sweep_board t;
  remove_squares t;
  is_filled_with_color t ~row:0 ~col:0 Color.Orange
  && is_filled_with_color t ~row:0 ~col:1 Color.White
;;
