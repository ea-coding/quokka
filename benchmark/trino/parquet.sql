create table lineitem (l_orderkey bigint, l_partkey bigint, l_suppkey bigint, l_linenumber bigint, l_quantity decimal(12,2), l_extendedprice decimal(12,2), l_discount decimal(12,2), l_tax decimal(12,2), l_returnflag char(1), l_linestatus char(1), l_shipdate date, l_commitdate date, l_receiptdate date, l_shipinstruct char(25), l_shipmode char(10), l_comment varchar ) WITH (format = 'parquet', external_location = 's3a://tpc-h-parquet/lineitem.parquet');
create table orders (o_orderkey bigint, o_custkey bigint, o_orderstatus char(1), o_totalprice decimal(12,2), o_orderdate date, o_orderpriority char(15), o_clerk char(15), o_shippriority int, o_comment varchar) WITH (format = 'parquet', external_location = 's3a://tpc-h-parquet/orders.parquet');
create table customer (c_custkey bigint, c_name char(25), c_address char(40), c_nationkey bigint, c_phone char(15), c_acctbal decimal(12,2), c_mktsegment char(10), c_comment char(17)) WITH (format = 'parquet', external_location = 's3a://tpc-h-parquet/customer.parquet');
create table part (p_partkey bigint, p_name varchar, p_mfgr char(25),p_brand char(10), p_type varchar ,p_size int, p_container char(10), p_retailprice decimal(12,2), p_comment varchar) WITH (format = 'parquet', external_location = 's3a://tpc-h-parquet/part.parquet');
create table supplier (s_suppkey bigint, s_name char(25), s_address varchar , s_nationkey bigint, s_phone char(15), s_acctbal decimal(12,2), s_comment varchar) WITH (format = 'parquet', external_location = 's3a://tpc-h-parquet/supplier.parquet');
create table partsupp (ps_partkey bigint, ps_suppkey bigint, ps_availqty bigint, ps_supplycost decimal(12,2), ps_comment varchar) WITH (format = 'parquet', external_location = 's3a://tpc-h-parquet/partsupp.parquet');
create table nation (n_nationkey bigint, n_name char(25), n_regionkey bigint , n_comment varchar) WITH (format = 'parquet', external_location = 's3a://tpc-h-parquet/nation.parquet');
create table region (r_regionkey bigint, r_name varchar, r_comment varchar) WITH (format = 'parquet', external_location = 's3a://tpc-h-parquet/region.parquet');

create table lineitem (l_orderkey bigint, l_partkey bigint, l_suppkey bigint, l_linenumber bigint, l_quantity decimal(12,2), l_extendedprice decimal(12,2), l_discount decimal(12,2), l_tax decimal(12,2), l_returnflag char(1), l_linestatus char(1), l_shipdate date, l_commitdate date, l_receiptdate date, l_shipinstruct char(25), l_shipmode char(10), l_comment varchar ) WITH (format = 'parquet', external_location = 's3a://tpc-h-parquet-1tb-iceberg/tpch1tb.db/lineitem/data/');
create table orders (o_orderkey bigint, o_custkey bigint, o_orderstatus char(1), o_totalprice decimal(12,2), o_orderdate date, o_orderpriority char(15), o_clerk char(15), o_shippriority int, o_comment varchar) WITH (format = 'parquet', external_location = 's3a://tpc-h-parquet-1tb-iceberg/tpch1tb.db/orders/data/');
create table customer (c_custkey bigint, c_name char(25), c_address char(40), c_nationkey bigint, c_phone char(15), c_acctbal decimal(12,2), c_mktsegment char(10), c_comment char(17)) WITH (format = 'parquet', external_location = 's3a://tpc-h-parquet-1tb-iceberg/tpch1tb.db/customer/data/');
create table part (p_partkey bigint, p_name varchar, p_mfgr char(25),p_brand char(10), p_type varchar ,p_size int, p_container char(10), p_retailprice decimal(12,2), p_comment varchar) WITH (format = 'parquet', external_location = 's3a://tpc-h-parquet-1tb-iceberg/tpch1tb.db/part/data/');
create table supplier (s_suppkey bigint, s_name char(25), s_address varchar , s_nationkey bigint, s_phone char(15), s_acctbal decimal(12,2), s_comment varchar) WITH (format = 'parquet', external_location = 's3a://tpc-h-parquet-1tb-iceberg/tpch1tb.db/supplier/data/');
create table partsupp (ps_partkey bigint, ps_suppkey bigint, ps_availqty bigint, ps_supplycost decimal(12,2), ps_comment varchar) WITH (format = 'parquet', external_location = 's3a://tpc-h-parquet-1tb-iceberg/tpch1tb.db/partsupp/data/');
create table nation (n_nationkey bigint, n_name char(25), n_regionkey bigint , n_comment varchar) WITH (format = 'parquet', external_location = 's3a://tpc-h-parquet-1tb-iceberg/tpch1tb.db/nation/data/');
create table region (r_regionkey bigint, r_name varchar, r_comment varchar) WITH (format = 'parquet', external_location = 's3a://tpc-h-parquet-1tb-iceberg/tpch1tb.db/region/data/');

create table lineitem (l_orderkey bigint, l_partkey bigint, l_suppkey bigint, l_linenumber bigint, l_quantity decimal(12,2), l_extendedprice decimal(12,2), l_discount decimal(12,2), l_tax decimal(12,2), l_returnflag char(1), l_linestatus char(1), l_shipdate date, l_commitdate date, l_receiptdate date, l_shipinstruct char(25), l_shipmode char(10), l_comment varchar ) WITH (format = 'parquet', external_location = 's3a://tpc-h-parquet-100/lineitem.parquet/');
create table orders (o_orderkey bigint, o_custkey bigint, o_orderstatus char(1), o_totalprice decimal(12,2), o_orderdate date, o_orderpriority char(15), o_clerk char(15), o_shippriority int, o_comment varchar) WITH (format = 'parquet', external_location = 's3a://tpc-h-parquet-100/orders.parquet/');
create table customer (c_custkey bigint, c_name char(25), c_address char(40), c_nationkey bigint, c_phone char(15), c_acctbal decimal(12,2), c_mktsegment char(10), c_comment char(17)) WITH (format = 'parquet', external_location = 's3a://tpc-h-parquet-100/customer.parquet/');
create table part (p_partkey bigint, p_name varchar, p_mfgr char(25),p_brand char(10), p_type varchar ,p_size int, p_container char(10), p_retailprice decimal(12,2), p_comment varchar) WITH (format = 'parquet', external_location = 's3a://tpc-h-parquet-100/part.parquet/');
create table supplier (s_suppkey bigint, s_name char(25), s_address varchar , s_nationkey bigint, s_phone char(15), s_acctbal decimal(12,2), s_comment varchar) WITH (format = 'parquet', external_location = 's3a://tpc-h-parquet-100/supplier.parquet/');
create table partsupp (ps_partkey bigint, ps_suppkey bigint, ps_availqty bigint, ps_supplycost decimal(12,2), ps_comment varchar) WITH (format = 'parquet', external_location = 's3a://tpc-h-parquet-100/partsupp.parquet/');
create table nation (n_nationkey bigint, n_name char(25), n_regionkey bigint , n_comment varchar) WITH (format = 'parquet', external_location = 's3a://tpc-h-parquet-100/nation.parquet/');
create table region (r_regionkey bigint, r_name varchar, r_comment varchar) WITH (format = 'parquet', external_location = 's3a://tpc-h-parquet-100/region.parquet/');

use default;
create table lineitem using parquet location 's3://tpc-h-parquet-100-native-mine/lineitem.parquet/';
create table orders using parquet location 's3://tpc-h-parquet-100-native-mine/orders.parquet/';
create table customer using parquet location 's3://tpc-h-parquet-100-native-mine/customer.parquet/';
create table part using parquet location 's3://tpc-h-parquet-100-native-mine/part.parquet/';
create table supplier using parquet location 's3://tpc-h-parquet-100-native-mine/supplier.parquet/';
create table partsupp using parquet location 's3://tpc-h-parquet-100-native-mine/partsupp.parquet/';
create table nation using parquet location 's3://tpc-h-parquet-100-native-mine/nation.parquet/';
create table region using parquet location 's3://tpc-h-parquet-100-native-mine/region.parquet/';

analyze table lineitem compute statistics for all columns;
analyze table orders compute statistics for all columns;
analyze table customer compute statistics for all columns;
analyze table part compute statistics for all columns;
analyze table supplier compute statistics for all columns;
analyze table partsupp compute statistics for all columns;
analyze table nation compute statistics for all columns;
analyze table region compute statistics for all columns;


create table lineitem (l_orderkey bigint, l_partkey bigint, l_suppkey bigint, l_linenumber bigint, l_quantity decimal(12,2), l_extendedprice decimal(12,2), l_discount decimal(12,2), l_tax decimal(12,2), l_returnflag varchar(1), l_linestatus varchar(1), l_shipdate date, l_commitdate date, l_receiptdate date, l_shipinstruct varchar(25), l_shipmode varchar(10), l_comment varchar(44) ) using csv options (header = "false", delimiter = "|", path = 's3://tpc-h-csv-100-mine/lineitem.tbl');
create table orders (o_orderkey bigint, o_custkey bigint, o_orderstatus varchar(1), o_totalprice decimal(12,2), o_orderdate date, o_orderpriority varchar(15), o_clerk varchar(15), o_shippriority int, o_comment varchar(79)) using csv options (header = "false", delimiter = "|", path = 's3://tpc-h-csv-100-mine/orders.tbl');
create table customer (c_custkey bigint, c_name varchar(25), c_address varchar(40), c_nationkey bigint, c_phone varchar(15), c_acctbal decimal(12,2), c_mktsegment varchar(10), c_comment varchar(117)) using csv options (header = "false", delimiter = "|", path = 's3://tpc-h-csv-100-mine/customer.tbl');
create table part (p_partkey bigint, p_name varchar(55), p_mfgr varchar(25),p_brand varchar(10), p_type varchar(25) ,p_size int, p_container varchar(10), p_retailprice decimal(12,2), p_comment varchar(23)) using csv options (header = "false", delimiter = "|", path = 's3://tpc-h-csv-100-mine/part.tbl');
create table supplier (s_suppkey bigint, s_name varchar(25), s_address varchar(25) , s_nationkey bigint, s_phone varchar(15), s_acctbal decimal(12,2), s_comment varchar(101)) using csv options (header = "false", delimiter = "|", path = 's3://tpc-h-csv-100-mine/supplier.tbl');
create table partsupp (ps_partkey bigint, ps_suppkey bigint, ps_availqty bigint, ps_supplycost decimal(12,2), ps_comment varchar(199)) using csv options (header = "false", delimiter = "|", path = 's3://tpc-h-csv-100-mine/partsupp.tbl');
create table nation (n_nationkey bigint, n_name varchar(25), n_regionkey bigint , n_comment varchar(152)) using csv options (header = "false", delimiter = "|", path = 's3://tpc-h-csv-100-mine/nation.tbl');
create table region (r_regionkey bigint, r_name varchar(25), r_comment varchar(152)) using csv options (header = "false", delimiter = "|", path = 's3://tpc-h-csv-100-mine/region.tbl');