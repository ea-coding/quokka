class OutputS3CSVExecutor(Executor):
    def __init__(self, bucket, prefix, output_line_limit = 1000000) -> None:
        self.num = 0

        self.bucket = bucket
        self.prefix = prefix
        self.output_line_limit = output_line_limit
        self.name = 0
        self.my_batches = deque()
        self.exe = None
        self.executor_id = None
        self.session = get_session()

    def serialize(self):
        return {}, "all"
    
    def deserialize(self, s):
        pass

    def create_csv_file(self, data):
        da = BytesIO()
        csv.write_csv(data.to_arrow(), da,  write_options = csv.WriteOptions(include_header=False))
        return da

    async def do(self, client, data, name):
        da = await asyncio.get_running_loop().run_in_executor(self.exe, self.create_csv_file, data)
        resp = await client.put_object(Bucket=self.bucket,Key=self.prefix + "-" + str(self.executor_id) + "-" + str(name) + ".csv",Body=da.getvalue())
        #print(resp)

    async def go(self, datas):
        # this is expansion of async with, so you don't have to remake the client
        
        async with self.session.create_client("s3", region_name="us-west-2") as client:
            todos = []
            for i in range(len(datas)):
                todos.append(self.do(client,datas[i], self.name))
                self.name += 1
        
            await asyncio.gather(*todos)
        
    def execute(self,batches,stream_id, executor_id):

        if self.exe is None:
            self.exe = concurrent.futures.ThreadPoolExecutor(max_workers = 2)
        if self.executor_id is None:
            self.executor_id = executor_id
        else:
            assert self.executor_id == executor_id

        self.my_batches.extend([i for i in batches if i is not None])
        #print("MY OUTPUT CSV STATE", [len(i) for i in self.my_batches] )

        curr_len = 0
        i = 0
        datas = []
        process = psutil.Process(os.getpid())
        print("mem usage output", process.memory_info().rss, pa.total_allocated_bytes())
        while i < len(self.my_batches):
            curr_len += len(self.my_batches[i])
            #print(curr_len)
            i += 1
            if curr_len > self.output_line_limit:
                #print("writing")
                datas.append(polars.concat([self.my_batches.popleft() for k in range(i)], rechunk = True))
                i = 0
                curr_len = 0
        #print("writing ", len(datas), " files")
        asyncio.run(self.go(datas))
        #print("mem usage after", process.memory_info().rss, pa.total_allocated_bytes())

    def done(self,executor_id):
        if len(self.my_batches) > 0:
            datas = [polars.concat(list(self.my_batches), rechunk=True)]
            asyncio.run(self.go(datas))
        print("done")

class OutputS3ParquetFastExecutor(Executor):
    def __init__(self, bucket, prefix, output_line_limit = 10000000) -> None:
        self.num = 0
        self.bucket = bucket
        self.prefix = prefix
        self.output_line_limit = output_line_limit
        self.name = 0
        self.my_batches = deque()
        self.exe = None
        self.executor_id = None
        self.client = None

    def serialize(self):
        return {}, "all"
    
    def deserialize(self, s):
        pass

    def create_parquet_file(self, data, name):
        writer = pa.BufferOutputStream()
        pq.write_table(data.to_arrow(), writer)
        resp = self.client.put_object(Bucket=self.bucket,Key=self.prefix + "-" + str(self.executor_id) + "-" + str(name) + ".parquet",Body=bytes(writer.getvalue()))
        return resp

    async def do(self, data,  name):
        da = await asyncio.get_running_loop().run_in_executor(self.exe, self.create_parquet_file, data, name)
        print(da)

    async def go(self, datas):
        # this is expansion of async with, so you don't have to remake the client
        todos = []
        for i in range(len(datas)):
            todos.append(self.do(datas[i], self.name))
            self.name += 1
    
        await asyncio.gather(*todos)
        
    def execute(self,batches,stream_id, executor_id):

        if self.exe is None:
            self.exe = concurrent.futures.ThreadPoolExecutor(max_workers = 8)
        if self.executor_id is None:
            self.executor_id = executor_id
        else:
            assert self.executor_id == executor_id
        
        if self.client is None:
            self.client = boto3.client("s3")

        print("LEN BATCHES", len(batches))
        self.my_batches.extend([i for i in batches if i is not None])
        #print("MY OUTPUT CSV STATE", [len(i) for i in self.my_batches] )

        curr_len = 0
        i = 0
        datas = []
        process = psutil.Process(os.getpid())
        #print("mem usage output", process.memory_info().rss, pa.total_allocated_bytes())
        while i < len(self.my_batches):
            curr_len += len(self.my_batches[i])
            #print(curr_len)
            i += 1
            if curr_len > self.output_line_limit:
                #print("writing")
                datas.append(polars.concat([self.my_batches.popleft() for k in range(i)], rechunk = True))
                i = 0
                curr_len = 0
        #print("writing ", len(datas), " files")
        asyncio.run(self.go(datas))
        #print("mem usage after", process.memory_info().rss, pa.total_allocated_bytes())

    def done(self,executor_id):
        if len(self.my_batches) > 0:
            datas = [polars.concat(list(self.my_batches), rechunk=True)]
            asyncio.run(self.go(datas))
        print("done")

# WARNING: this is currently extremely inefficient. But it is indeed very general.
# pyarrow joins do not support list data types 
class GenericGroupedAggExecutor(Executor):
    def __init__(self, funcs, final_func = None):

        # how many things you might checkpoint, the number of keys in the dict

        self.state = None
        self.funcs = funcs # this will be a dictionary of col name -> tuple of (merge func, fill_value)
        self.cols = list(funcs.keys())
        self.final_func = final_func

    def serialize(self):
        return {0:self.state}, "all"
    
    def deserialize(self, s):
        # the default is to get a list of dictionaries.
        assert type(s) == list and len(s) == 1
        self.state = s[0][0]
    
    def execute(self,batches, stream_id, executor_id):
        batches = [i for i in batches if i is not None]
        for batch in batches:
            assert type(batch) == pd.core.frame.DataFrame # polars add has no index, will have wierd behavior
            if self.state is None:
                self.state = batch 
            else:
                self.state = self.state[self.cols].join(batch[self.cols],lsuffix="_bump",how="outer")
                for col in self.cols:
                    func, fill_value = self.funcs[col]
                    isna = self.state[col].isna()
                    self.state.loc[isna, [col]] = pd.Series([fill_value] * isna.sum()).values
                    isna = self.state[col + "_bump"].isna()
                    self.state.loc[isna, [col + "_bump"]] = pd.Series([fill_value] * isna.sum()).values
                    self.state[col] = func(self.state[col], self.state[col + "_bump"])
                    self.state.drop(columns = [col+"_bump"], inplace=True)
                    
    
    def done(self,executor_id):
        if self.final_func:
            return self.final_func(self.state)
        else:
            #print(self.state)
            return self.state

class AddExecutor(Executor):
    def __init__(self, fill_value = 0, final_func = None):

        # how many things you might checkpoint, the number of keys in the dict
        self.num_states = 1

        self.state = None
        self.fill_value = fill_value
        self.final_func = final_func

    def serialize(self):
        return {0:self.state}, "all"
    
    def deserialize(self, s):
        # the default is to get a list of dictionaries.
        assert type(s) == list and len(s) == 1
        self.state = s[0][0]
    
    # the execute function signature does not change. stream_id will be a [0 - (length of InputStreams list - 1)] integer
    def execute(self,batches, stream_id, executor_id):
        batches = [i for i in batches if i is not None]
        for batch in batches:
            assert type(batch) == pd.core.frame.DataFrame # polars add has no index, will have wierd behavior
            if self.state is None:
                self.state = batch 
            else:
                self.state = self.state.add(batch, fill_value = self.fill_value)
    
    def done(self,executor_id):
        if self.final_func:
            return self.final_func(self.state)
        else:
            #print(self.state)
            return self.state

class GroupAsOfJoinExecutor():
    # batch func here expects a list of dfs. This is a quark of the fact that join results could be a list of dfs.
    # batch func must return a list of dfs too
    def __init__(self, group_on= None, group_left_on = None, group_right_on = None, on = None, left_on = None, right_on = None, suffix="_right"):

        self.trade = {}
        self.quote = {}
        self.ckpt_start0 = 0
        self.ckpt_start1 = 0
        self.suffix = suffix

        if on is not None:
            assert left_on is None and right_on is None
            self.left_on = on
            self.right_on = on
        else:
            assert left_on is not None and right_on is not None
            self.left_on = left_on
            self.right_on = right_on
        
        if group_on is not None:
            assert group_left_on is None and group_right_on is None
            self.group_left_on = group_on
            self.group_right_on = group_on
        else:
            assert group_left_on is not None and group_right_on is not None
            self.group_left_on = group_left_on
            self.group_right_on = group_right_on

    def serialize(self):
        result = {0:self.trade, 1:self.quote}        
        return result, "all"
    
    def deserialize(self, s):
        assert type(s) == list
        self.trade = s[0][0]
        self.quote = s[0][1]
    
    def find_second_smallest(self, batch, key):
        smallest = batch[0][key]
        for i in range(len(batch)):
            if batch[i][key] > smallest:
                return batch[i][key]
    
    # the execute function signature does not change. stream_id will be a [0 - (length of InputStreams list - 1)] integer
    def execute(self,batches, stream_id, executor_id):
        # state compaction
        batches = [i for i in batches if len(i) > 0]
        if len(batches) == 0:
            return
        
        # self.trade will be a dictionary of lists. 
        # self.quote will be a dictionary of lists.

        # trade
        ret_vals = []
        if stream_id == 0:
            for batch in batches:
                frames = batch.partition_by(self.group_left_on)
                for trade_chunk in frames:
                    symbol = trade_chunk["symbol"][0]
                    min_trade_ts = trade_chunk[self.left_on][0]
                    max_trade_ts = trade_chunk[self.left_on][-1]
                    if symbol not in self.quote:
                        if symbol in self.trade:
                            self.trade[symbol].append(trade_chunk)
                        else:
                            self.trade[symbol] = [trade_chunk]
                        continue
                    current_quotes_for_symbol = self.quote[symbol]
                    for i in range(len(current_quotes_for_symbol)):
                        quote_chunk = current_quotes_for_symbol[i]
                        min_quote_ts = quote_chunk[self.right_on][0]
                        max_quote_ts = quote_chunk[self.right_on][-1]
                        #print(max_trade_ts, min_quote_ts, min_trade_ts, max_quote_ts)
                        if max_trade_ts < min_quote_ts or min_trade_ts > max_quote_ts:
                            # no overlap.
                            continue
                        else:
                            second_smallest_quote_ts = self.find_second_smallest(quote_chunk, self.right_on)
                            joinable_trades = trade_chunk[(trade_chunk[self.left_on] >= second_smallest_quote_ts) & (trade_chunk[self.left_on] < max_quote_ts)]
                            if len(joinable_trades) == 0:
                                continue
                            trade_start_ts = joinable_trades[self.left_on][0]
                            trade_end_ts = joinable_trades[self.left_on][-1]
                            if len(joinable_trades) == 0:
                                continue
                            quote_start_ts = quote_chunk[self.right_on][quote_chunk[self.right_on] <= trade_start_ts][-1]
                            quote_end_ts = quote_chunk[self.right_on][quote_chunk[self.right_on] <= trade_end_ts][-1]
                            joinable_quotes = quote_chunk[(quote_chunk[self.right_on] >= quote_start_ts) & (quote_chunk[self.right_on] <= quote_end_ts)]
                            if len(joinable_quotes) == 0:
                                continue
                            trade_chunk = trade_chunk[(trade_chunk[self.left_on] < trade_start_ts) | (trade_chunk[self.left_on] > trade_end_ts)]
                            new_chunk = quote_chunk[(quote_chunk[self.right_on] < quote_start_ts) | (quote_chunk[self.left_on] > quote_end_ts)]
                            
                            self.quote[symbol][i] = new_chunk
                            
                            ret_vals.append(joinable_trades.join_asof(joinable_quotes.drop(self.group_right_on), left_on = self.left_on, right_on = self.right_on))
                            if len(trade_chunk) == 0:
                                break
                    
                    self.quote[symbol] = [i for i in self.quote[symbol] if len(i) > 0]

                    if len(trade_chunk) == 0:
                        continue
                    if symbol in self.trade:
                        self.trade[symbol].append(trade_chunk)
                    else:
                        self.trade[symbol] = [trade_chunk]
        #quote
        elif stream_id == 1:
            for batch in batches:
                frames = batch.partition_by(self.group_right_on)
                for quote_chunk in frames:
                    symbol = quote_chunk["symbol"][0]
                    min_quote_ts = quote_chunk[self.right_on][0]
                    max_quote_ts = quote_chunk[self.right_on][-1]
                    if symbol not in self.trade:
                        if symbol in self.quote:
                            self.quote[symbol].append(quote_chunk)
                        else:
                            self.quote[symbol] = [quote_chunk]
                        continue
                        
                    current_trades_for_symbol = self.trade[symbol]
                    for i in range(len(current_trades_for_symbol)):
                        trade_chunk = current_trades_for_symbol[i]
                        #print(current_trades_for_symbol)
                        min_trade_ts = trade_chunk[self.left_on][0]
                        max_trade_ts = trade_chunk[self.left_on][-1]
                        if max_trade_ts < min_quote_ts or min_trade_ts > max_quote_ts:
                            # no overlap.
                            continue
                        else:
                            second_smallest_quote_ts = self.find_second_smallest(quote_chunk, self.right_on)
                            joinable_trades = trade_chunk[(trade_chunk[self.left_on] >= second_smallest_quote_ts) &( trade_chunk[self.left_on] < max_quote_ts)]
                            if len(joinable_trades) == 0:
                                continue
                            trade_start_ts = joinable_trades[self.left_on][0]
                            trade_end_ts = joinable_trades[self.left_on][-1]
                            if len(joinable_trades) == 0:
                                continue
                            quote_start_ts = quote_chunk[self.right_on][quote_chunk[self.right_on] <= trade_start_ts][-1]
                            quote_end_ts = quote_chunk[self.right_on][quote_chunk[self.right_on] <= trade_end_ts][-1]
                            joinable_quotes = quote_chunk[(quote_chunk[self.right_on] >= quote_start_ts) & (quote_chunk[self.right_on] <= quote_end_ts)]
                            if len(joinable_quotes) == 0:
                                continue
                            quote_chunk = quote_chunk[(quote_chunk[self.right_on] < quote_start_ts ) | (quote_chunk[self.left_on] > quote_end_ts)]
                            new_chunk = trade_chunk[(trade_chunk[self.left_on] < trade_start_ts) | (trade_chunk[self.left_on] > trade_end_ts)]
                            
                            self.trade[symbol][i] = new_chunk

                            ret_vals.append(joinable_trades.join_asof(joinable_quotes.drop(self.group_right_on), left_on = self.left_on, right_on = self.right_on))
                            if len(quote_chunk) == 0:
                                break
                    
                    self.trade[symbol] = [i for i in self.trade[symbol] if len(i) > 0]
                    if len(quote_chunk) == 0:
                        continue
                    if symbol in self.quote:
                        self.quote[symbol].append(quote_chunk)
                    else:
                        self.quote[symbol] = [quote_chunk]
        #print(ret_vals)

        if len(ret_vals) == 0:
            return
        for thing in ret_vals:
            print(len(thing))
            print(thing[thing.symbol=="ZU"])
        result = polars.concat(ret_vals).drop_nulls()

        if result is not None and len(result) > 0:
            return result
    
    def done(self,executor_id):
        #print(len(self.state0),len(self.state1))
        ret_vals = []
        for symbol in self.trade:
            if symbol not in self.quote:
                continue
            else:
                trades = polars.concat(self.trade[symbol]).sort(self.left_on)
                quotes = polars.concat(self.quote[symbol]).sort(self.right_on)
                ret_vals.append(trades.join_asof(quotes.drop(self.group_right_on), left_on = self.left_on, right_on = self.right_on, suffix=self.suffix))
        
        print("done asof join ", executor_id)
        return polars.concat(ret_vals).drop_nulls()

class AggExecutor(Executor):
    '''
    aggregation_dict will define what you are going to do for
    '''
    def __init__(self, groupby_keys, orderby_keys, aggregation_dict, mean_cols, count):


        self.state = None
        self.emit_count = count
        assert type(groupby_keys) == list and len(groupby_keys) > 0
        self.groupby_keys = groupby_keys
        self.aggregation_dict = aggregation_dict
        self.mean_cols = mean_cols
        self.length_limit = 1000000
        # hope and pray there is no column called __&&count__
        self.pyarrow_agg_list = [("__count_sum", "sum")]
        self.count_col = "__count_sum"
        self.rename_dict = {"__count_sum_sum": self.count_col}
        for key in aggregation_dict:
            assert aggregation_dict[key] in {
                    "max", "min", "mean", "sum"}, "only support max, min, mean and sum for now"
            if aggregation_dict[key] == "mean":
                self.pyarrow_agg_list.append((key, "sum"))
                self.rename_dict[key + "_sum"] = key
            else:
                self.pyarrow_agg_list.append((key, aggregation_dict[key]))
                self.rename_dict[key + "_" + aggregation_dict[key]] = key
        
        self.order_list = []
        self.reverse_list = []
        if orderby_keys is not None:
            for key, dir in orderby_keys:
                self.order_list.append(key)
                self.reverse_list.append(True if dir == "desc" else False)

    def checkpoint(self, conn, actor_id, channel_id, seq):
        pass
    
    def restore(self, conn, actor_id, channel_id, seq):
        pass
    
    # the execute function signature does not change. stream_id will be a [0 - (length of InputStreams list - 1)] integer
    def execute(self,batches, stream_id, executor_id):

        batches = [polars.from_arrow(i) for i in batches if i is not None]
        batch = polars.concat(batches)
        assert type(batch) == polars.internals.DataFrame, batch # polars add has no index, will have wierd behavior
        if self.state is None:
            self.state = batch
        else:
            self.state = self.state.vstack(batch)
        if len(self.state) > self.length_limit:
            arrow_state = self.state.to_arrow()
            arrow_state = arrow_state.group_by(self.groupby_keys).aggregate(self.pyarrow_agg_list)
            self.state = polars.from_arrow(arrow_state).rename(self.rename_dict)
            self.state = self.state.select(sorted(self.state.columns))


    def done(self,executor_id):

        # print("done", time.time())

        if self.state is None:
            return None
        
        arrow_state = self.state.to_arrow()
        arrow_state = arrow_state.group_by(self.groupby_keys).aggregate(self.pyarrow_agg_list)
        self.state = polars.from_arrow(arrow_state).rename(self.rename_dict)

        for key in self.aggregation_dict:
            if self.aggregation_dict[key] == "mean":
                self.state = self.state.with_column(polars.Series(key, self.state[key]/ self.state[self.count_col]))
        
        for key in self.mean_cols:
            keep_sum = self.mean_cols[key]
            self.state = self.state.with_column(polars.Series(key + "_mean", self.state[key + "_sum"]/ self.state[self.count_col]))
            if not keep_sum:
                self.state = self.state.drop(key + "_sum")
        
        if not self.emit_count:
            self.state = self.state.drop(self.count_col)
        
        if len(self.order_list) > 0:
            return self.state.sort(self.order_list, self.reverse_list)
        else:
            return self.state

class MergeSortedExecutor(Executor):
    def __init__(self, key, record_batch_rows = None, length_limit = 5000, file_prefix = "mergesort") -> None:
        self.states = []
        self.num = 1
        self.key = key
        self.record_batch_rows = record_batch_rows
        self.fileno = 0
        self.length_limit = length_limit
        self.prefix = file_prefix # make sure this is different for different executors

        self.filename_to_size = {}
        self.data_dir = "/data"
    
    def serialize(self):
        return {}, "all" # don't support fault tolerance of sort
    
    def deserialize(self, s):
        raise Exception

    def write_out_df_to_disk(self, target_filepath, input_mem_table):
        arrow_table = input_mem_table.to_arrow()
        batches = arrow_table.to_batches(self.record_batch_rows)
        writer =  pa.ipc.new_file(pa.OSFile(target_filepath, 'wb'), arrow_table.schema)
        for batch in batches:
            writer.write(batch)
        writer.close()
    
    # with minimal memory used!
    def produce_sorted_file_from_two_sorted_files(self, target_filepath, input_filepath1, input_filepath2):

        read_time = 0
        sort_time = 0
        write_time = 0

        source1 =  pa.ipc.open_file(pa.memory_map(input_filepath1, 'rb'))
        number_of_batches_in_source1 = source1.num_record_batches
        source2 =  pa.ipc.open_file(pa.memory_map(input_filepath2, 'rb'))
        number_of_batches_in_source2 = source2.num_record_batches

        next_batch_to_get1 = 1

        start = time.time()
        cached_batches_in_mem1 = polars.from_arrow(pa.Table.from_batches([source1.get_batch(0)]))
        next_batch_to_get2 = 1
        cached_batches_in_mem2 = polars.from_arrow(pa.Table.from_batches([source2.get_batch(0)]))
        read_time += time.time() - start

        writer =  pa.ipc.new_file(pa.OSFile(target_filepath, 'wb'), source1.schema)

        # each iteration will write a batch to the target filepath
        while len(cached_batches_in_mem1) > 0 and len(cached_batches_in_mem2) > 0:
            
            disk_portion1 = cached_batches_in_mem1[:self.record_batch_rows]
            disk_portion1['asdasd'] = np.zeros(len(disk_portion1))

            disk_portion2 = cached_batches_in_mem2[:self.record_batch_rows]
            disk_portion2['asdasd'] = np.ones(len(disk_portion2))
            
            start = time.time()
            new_batch = polars.concat([disk_portion1, disk_portion2]).sort(self.key)[:self.record_batch_rows]

            result_idx = polars.concat([disk_portion1.select([self.key, "asdasd"]), disk_portion2.select([self.key, "asdasd"])]).sort(self.key)[:self.record_batch_rows]
            disk_contrib2 = int(result_idx["asdasd"].sum())
            disk_contrib1 = len(result_idx) - disk_contrib2
            
            new_batch = polars.concat([disk_portion1[:disk_contrib1], disk_portion2[:disk_contrib2]]).sort(self.key)[:self.record_batch_rows]
            new_batch.drop_in_place('asdasd')
            sort_time += time.time() - start

            #print(source.schema, new_batch.to_arrow().schema)
            start = time.time()
            writer.write(new_batch.to_arrow().to_batches()[0])
            write_time += time.time() - start

            cached_batches_in_mem1 = cached_batches_in_mem1[disk_contrib1:]
            
            start = time.time()
            if len(cached_batches_in_mem1) < self.record_batch_rows and next_batch_to_get1 < number_of_batches_in_source1:
                next_batch = source1.get_batch(next_batch_to_get1)
                next_batch_to_get1 += 1
                next_batch = polars.from_arrow(pa.Table.from_batches([next_batch]))
                cached_batches_in_mem1 = cached_batches_in_mem1.vstack(next_batch)
            
            cached_batches_in_mem2 = cached_batches_in_mem2[disk_contrib2:]
            if len(cached_batches_in_mem2) < self.record_batch_rows and next_batch_to_get2 < number_of_batches_in_source2:
                next_batch = source2.get_batch(next_batch_to_get2)
                next_batch_to_get2 += 1
                next_batch = polars.from_arrow(pa.Table.from_batches([next_batch]))
                cached_batches_in_mem2 = cached_batches_in_mem2.vstack(next_batch)
            
            read_time += time.time() - start

        
        writer.close()

        process = psutil.Process(os.getpid())
        print("mem usage", process.memory_info().rss, pa.total_allocated_bytes())
        print(read_time, write_time, sort_time)

    def done(self, executor_id):
        
        # first merge all of the in memory states to a file. This makes programming easier and likely not horrible in terms of performance. And we can save some memory! 
        # yolo and hope that that you can concatenate all and not die
        if len(self.states) > 0:
            in_mem_state = polars.concat(self.states).sort(self.key)
            self.write_out_df_to_disk(self.data_dir + "/" + self.prefix + "-" + str(executor_id) + "-" + str(self.fileno) + ".arrow", in_mem_state)
            self.filename_to_size[self.fileno] = len(in_mem_state)
            self.fileno += 1
            del in_mem_state
        self.states = []

        # now all the states should be strs!
        print("MY DISK STATE", self.filename_to_size.keys())
        sources = [self.data_dir + "/" + self.prefix + "-" + str(executor_id) + "-" + str(k) + ".arrow" for k in self.filename_to_size]
        return sources
    
    # this is some crazy wierd algo that I came up with, might be there before.
    def execute(self, batches, stream_id, executor_id):
        print("NUMBER OF INCOMING BATCHES", len(batches))
        #print("MY SORT STATE", [(type(i), len(i)) for i in self.states if type(i) == polars.internals.DataFrame])
        import os, psutil
        process = psutil.Process(os.getpid())
        print("mem usage", process.memory_info().rss, pa.total_allocated_bytes())
        batches = deque([batch for batch in batches if batch is not None and len(batch) > 0])
        if len(batches) == 0:
            return

        while len(batches) > 0:
            batch = batches.popleft()
            #batch = batch.sort(self.key)
            print("LENGTH OF INCOMING BATCH", len(batch))
            
            if self.record_batch_rows is None:
                self.record_batch_rows = len(batch)

            if len(batch) > self.length_limit:
                self.write_out_df_to_disk(self.data_dir + "/" + self.prefix + "-" + str(executor_id) + "-" + str(self.fileno) + ".arrow", batch)
                self.filename_to_size[self.fileno] = len(batch)
                self.fileno += 1
            elif sum([len(i) for i in self.states if type(i) == polars.internals.DataFrame]) + len(batch) > self.length_limit:
                mega_batch = polars.concat([i for i in self.states if type(i) == polars.internals.DataFrame] + [batch]).sort(self.key)
                self.write_out_df_to_disk(self.data_dir + "/" + self.prefix + "-" + str(executor_id) + "-" + str(self.fileno) + ".arrow", mega_batch)
                self.filename_to_size[self.fileno] = len(mega_batch)
                del mega_batch
                self.fileno += 1
                self.states = []
            else:
                self.states.append(batch)
            
            while len(self.filename_to_size) > 4:
                files_to_merge = [y[0] for y in sorted(self.filename_to_size.items(), key = lambda x: x[1])[:2]]
                self.produce_sorted_file_from_two_sorted_files(self.data_dir + "/" + self.prefix + "-" + str(executor_id) + "-" + str(self.fileno) + ".arrow", 
                self.data_dir + "/" + self.prefix + "-" + str(executor_id) + "-" + str(files_to_merge[0]) + ".arrow",
                self.data_dir + "/" + self.prefix + "-" + str(executor_id) + "-" + str(files_to_merge[1]) + ".arrow")
                self.filename_to_size[self.fileno] = self.filename_to_size.pop(files_to_merge[0]) + self.filename_to_size.pop(files_to_merge[1])
                self.fileno += 1
                os.remove(self.data_dir + "/" + self.prefix + "-" + str(executor_id) + "-" + str(files_to_merge[0]) + ".arrow")
                os.remove(self.data_dir + "/" + self.prefix + "-" + str(executor_id) + "-" + str(files_to_merge[1]) + ".arrow")

class DuckAggExecutor(Executor):

    def __init__(self, groupby_keys, orderby_keys, aggregation_dict, mean_cols, count):

        self.state = None
        self.emit_count = count
        self.do_count = count
        assert type(groupby_keys) == list
        self.groupby_keys = groupby_keys
        self.mean_cols = mean_cols
        self.con = None        
        
        # we could use SQLGlot here but that's overkill.
        self.agg_clause = "select"
        for key in groupby_keys:
            self.agg_clause += "\n\t" + key + ","
        
        for key in aggregation_dict:
            agg_type = aggregation_dict[key]
            assert agg_type in {
                    "max", "min", "mean", "sum"}, "only support max, min, mean and sum for now"
            if agg_type == "mean":
                self.do_count = True
                self.agg_clause += "\n\tsum(" + key + ") as " + key + "_sum,"
            else:
                self.agg_clause += "\n\t" + agg_type + "(" + key + ") as " + key + "_" + agg_type + ","
        
        if self.do_count:
            self.agg_clause += "\n\tsum(__count_sum) as __count_sum,"
        
        # remove trailing comma
        self.agg_clause = self.agg_clause[:-1]
        self.agg_clause += "\nfrom\n\tbatch_arrow\n"
        if len(groupby_keys) > 0:
            self.agg_clause += "group by "
            for key in groupby_keys:
                self.agg_clause += key + ","
            self.agg_clause = self.agg_clause[:-1]

        if orderby_keys is not None:
            self.agg_clause += "\norder by "
            for key, dir in orderby_keys:
                if dir == "desc":
                    self.agg_clause += key + " desc,"
                else:
                    self.agg_clause += key + ","
            self.agg_clause = self.agg_clause[:-1]
        # print(self.agg_clause)

    def checkpoint(self, conn, actor_id, channel_id, seq):
        pass
    
    def restore(self, conn, actor_id, channel_id, seq):
        pass
    
    def execute(self,batches, stream_id, executor_id):

        batch = pa.concat_tables(batches)
        self.state = batch if self.state is None else pa.concat_tables([self.state, batch])
    
    def done(self, executor_id):

        if self.state is None:
            return None
        con = duckdb.connect().execute('PRAGMA threads=%d' % 8)
        batch_arrow = self.state
        self.state = polars.from_arrow(con.execute(self.agg_clause).arrow())
        del batch_arrow

        for key in self.mean_cols:
            keep_sum = self.mean_cols[key]
            self.state = self.state.with_column(polars.Series(key + "_mean", self.state[key + "_sum"]/ self.state[self.count_col]))
            if not keep_sum:
                self.state = self.state.drop(key + "_sum")
        
        if self.do_count and not self.emit_count:
            self.state = self.state.drop(self.count_col)
        
        return self.state

class XJoinExecutor(Executor):
    # batch func here expects a list of dfs. This is a quark of the fact that join results could be a list of dfs.
    # batch func must return a list of dfs too
    def __init__(self, on = None, left_on = None, right_on = None, how = "inner"):

        self.state0 = None
        self.state1 = None

        if on is not None:
            assert left_on is None and right_on is None
            self.left_on = on
            self.right_on = on
        else:
            assert left_on is not None and right_on is not None
            self.left_on = left_on
            self.right_on = right_on
        
        assert how in {"inner", "left",  "semi"}
        self.how = how
        if how == "inner":
            self.batch_how = "inner"
        elif how == "semi":
            self.batch_how = "semi"
        elif how == "left":
            self.batch_how = "inner"
        
        if how == "left" or how =="semi":
            self.left_null = None
            self.first_row_right = None # this is a hack to produce the left join NULLs at the end.
            self.left_null_last_ckpt = 0

        # keys that will never be seen again, safe to delete from the state on the other side

        self.state0_last_ckpt = 0
        self.state1_last_ckpt = 0
        self.s3fs = None
    
    def checkpoint(self, bucket, actor_id, channel_id, seq):
        # redis.Redis('localhost',port=6800).set(pickle.dumps(("ckpt", actor_id, channel_id, seq)), pickle.dumps((self.state0, self.state1)))
        
        if self.s3fs is None:
            self.s3fs = S3FileSystem()

        if self.state0 is not None:
            state0_to_ckpt = self.state0[self.state0_last_ckpt : ]
            self.state0_last_ckpt += len(state0_to_ckpt)
            pq.write_table(self.state0.to_arrow(), bucket + "/" + str(actor_id) + "-" + str(channel_id) + "-" + str(seq) + "-0.parquet", filesystem=self.s3fs)

        if self.state1 is not None:
            state1_to_ckpt = self.state1[self.state1_last_ckpt : ]
            self.state1_last_ckpt += len(state1_to_ckpt)
            pq.write_table(self.state1.to_arrow(), bucket + "/" + str(actor_id) + "-" + str(channel_id) + "-" + str(seq) + "-1.parquet", filesystem=self.s3fs)
        
    
    def restore(self, bucket, actor_id, channel_id, seq):
        # self.state0, self.state1 = pickle.loads(redis.Redis('localhost',port=6800).get(pickle.dumps(("ckpt", actor_id, channel_id, seq))))
        
        if self.s3fs is None:
            self.s3fs = S3FileSystem()
        try:
            print(bucket + "/" + str(actor_id) + "-" + str(channel_id) + "-" + str(seq) + "-0.parquet")
            self.state0 = polars.from_arrow(pq.read_table(bucket + "/" + str(actor_id) + "-" + str(channel_id) + "-" + str(seq) + "-0.parquet", filesystem=self.s3fs))
            print(self.state0)
        except:
            self.state0 = None
        try:
            print(bucket + "/" + str(actor_id) + "-" + str(channel_id) + "-" + str(seq) + "-1.parquet")
            self.state1 = polars.from_arrow(pq.read_table(bucket + "/" + str(actor_id) + "-" + str(channel_id) + "-" + str(seq) + "-1.parquet", filesystem=self.s3fs))
            print(self.state1)
        except:
            self.state1 = None

    # the execute function signature does not change. stream_id will be a [0 - (length of InputStreams list - 1)] integer
    def execute(self,batches, stream_id, executor_id):
        # state compaction
        batches = [polars.from_arrow(i) for i in batches if i is not None and len(i) > 0]
        if len(batches) == 0:
            return
        batch = polars.concat(batches)

        result = None
        new_left_null = None

        # if random.random() > 0.9 and redis.Redis('172.31.54.141',port=6800).get("input_already_failed") is None:
        #     redis.Redis('172.31.54.141',port=6800).set("input_already_failed", 1)
        #     ray.actor.exit_actor()
        # if random.random() > 0.9 and redis.Redis('localhost',port=6800).get("input_already_failed") is None:
        #     redis.Redis('localhost',port=6800).set("input_already_failed", 1)
        #     ray.actor.exit_actor()

        if stream_id == 0:
            if self.state1 is not None:
                result = batch.join(self.state1,left_on = self.left_on, right_on = self.right_on ,how=self.batch_how)
                if self.how == "left" or self.how == "semi":
                    new_left_null = batch.join(self.state1, left_on = self.left_on, right_on= self.right_on, how = "anti")
            else:
                if self.how == "left" or self.how == "semi":
                    new_left_null = batch

            if self.how != "semi":
                if self.state0 is None:
                    self.state0 = batch
                else:
                    self.state0.vstack(batch, in_place = True)

            if (self.how == "left" or self.how == "semi") and new_left_null is not None and len(new_left_null) > 0:
                if self.left_null is None:
                    self.left_null = new_left_null
                else:
                    self.left_null.vstack(new_left_null, in_place= True)
             
        elif stream_id == 1:

            if self.state0 is not None and self.how != "semi":
                result = self.state0.join(batch,left_on = self.left_on, right_on = self.right_on ,how=self.batch_how)
                
            if self.how == "semi" and self.left_null is not None:
                result = self.left_null.join(batch, left_on = self.left_on, right_on = self.right_on, how = "semi")
            
            if (self.how == "left" or self.how == "semi") and self.left_null is not None:
                self.left_null = self.left_null.join(batch, left_on = self.left_on, right_on = self.right_on, how = "anti")

            if self.state1 is None:
                if self.how == "left":
                    self.first_row_right = batch[0]
                self.state1 = batch
            else:
                self.state1.vstack(batch, in_place = True)
        
        if result is not None and len(result) > 0:
            return result
    
    def update_sources(self, remaining_sources):
        #print(remaining_sources)
        if self.how == "inner":
            if 0 not in remaining_sources:
                #print("DROPPING STATE!")
                self.state1 = None
            if 1 not in remaining_sources:
                #print("DROPPING STATE!")
                self.state0 = None
    
    def done(self,executor_id):
        self.update_sources({})
        #print(len(self.state0),len(self.state1))
        #print("done join ", executor_id)
        if self.how == "left" and self.left_null is not None and len(self.left_null) > 0:
            assert self.first_row_right is not None, "empty RHS"
            return self.left_null.join(self.first_row_right, left_on= self.left_on, right_on= self.right_on, how = "left")

        # print("DONE", executor_id)

class AntiJoinExecutor(Executor):
    # batch func here expects a list of dfs. This is a quark of the fact that join results could be a list of dfs.
    # batch func must return a list of dfs too
    def __init__(self, on = None, left_on = None, right_on = None, suffix="_right"):

        self.left_null = None
        self.state1 = None
        self.ckpt_start0 = 0
        self.ckpt_start1 = 0
        self.suffix = suffix

        if on is not None:
            assert left_on is None and right_on is None
            self.left_on = on
            self.right_on = on
        else:
            assert left_on is not None and right_on is not None
            self.left_on = left_on
            self.right_on = right_on
        
        self.batch_size = 1000000
        
        # keys that will never be seen again, safe to delete from the state on the other side
    
    # the execute function signature does not change. stream_id will be a [0 - (length of InputStreams list - 1)] integer
    def execute(self,batches, stream_id, executor_id):
        # state compaction
        batches = [polars.from_arrow(i) for i in batches if i is not None and len(i) > 0]
        if len(batches) == 0:
            return
        batch = polars.concat(batches)

        new_left_null = None

        if stream_id == 0:
            if self.state1 is not None:
                new_left_null = batch.join(self.state1, left_on = self.left_on, right_on= self.right_on, how = "anti", suffix = self.suffix)
            else:
                new_left_null = batch

            if new_left_null is not None and len(new_left_null) > 0:
                if self.left_null is None:
                    self.left_null = new_left_null
                else:
                    self.left_null.vstack(new_left_null, in_place= True)
             
        elif stream_id == 1:
            if self.left_null is not None:
                self.left_null = self.left_null.join(batch, left_on = self.left_on, right_on = self.right_on, how = "anti", suffix = self.suffix)
            
            if self.state1 is None:
                self.state1 = batch
            else:
                self.state1.vstack(batch, in_place = True)
    
    def done(self,executor_id):
        #print(len(self.state0),len(self.state1))
        #print("done join ", executor_id)
        if self.left_null is not None and len(self.left_null) > 0:
            for i in range(0, len(self.left_null), self.batch_size):
                yield self.left_null[i: i + self.batch_size]