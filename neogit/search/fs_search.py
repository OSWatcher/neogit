# Copyright 2021-2026 Mathieu Tarral
# SPDX-License-Identifier: Apache-2.0

from typing import Iterator, List, Optional, Union

from neo4j import Result, Session, Transaction

from neogit.model import FSSearchResult

SEARCH_RESULTS_LIMIT = 400


def search_by_filename(
    session: Union[Session, Transaction], os_sha1_list: Optional[List[str]], search_expr: str
) -> Iterator[FSSearchResult]:
    query = ["MATCH (o:Commit)-[:OWNS_FILESYSTEM]->(root:Tree)"]
    # filter OS if needed
    if os_sha1_list:
        # list is not None and not empty
        query.append("WHERE o.sha1sum IN $os_sha1_list")
    query.append("WITH o, root")
    # search filename
    query.append("MATCH path = (root)-[:HAS_CHILD_BLOB|HAS_CHILD_TREE*]->(b:Blob)")
    query.append("WITH relationships(path) as r_path, o")
    query.append("WITH last(r_path).name as filename, r_path, o")
    query.append("WHERE filename =~ $search_expr")
    query.append("RETURN o.name, o.sha1sum, apoc.text.join([r IN r_path | r.name], '/'), endNode(last(r_path)).sha1sum")
    # add limit
    query.append(f"LIMIT {SEARCH_RESULTS_LIMIT}")
    # run query
    query_str = "\n".join(query)
    result: Result = session.run(query_str, {"os_sha1_list": os_sha1_list, "search_expr": search_expr})
    for cursor in result:
        os_name, os_sha1, path, blob_sha1sum = cursor
        # path doesn't contain root, add it now
        path = f"/{path}"
        search_result = FSSearchResult(os_name, os_sha1, path, blob_sha1sum)
        yield search_result


def search_by_path(
    session: Union[Session, Transaction], os_sha1_list: Optional[List[str]], search_expr: str
) -> Iterator[FSSearchResult]:
    query = ["MATCH (o:Commit)-[:OWNS_FILESYSTEM]->(root:Tree)"]
    # filter OS if needed
    if os_sha1_list:
        # list is not None and not empty
        query.append("WHERE o.sha1sum IN $os_sha1_list")
    query.append("WITH o, root")
    # search filename
    query.append("MATCH path = (root)-[:HAS_CHILD_BLOB|HAS_CHILD_TREE*]->(b:Blob)")
    query.append("WITH relationships(path) as r_path, o")
    query.append("WITH apoc.text.join([r IN r_path | r.name], '/') as filepath, r_path, o")
    query.append("WHERE filepath =~ $search_expr")
    query.append("RETURN o.name, o.sha1sum, filepath, endNode(last(r_path)).sha1sum")
    # add limit
    query.append(f"LIMIT {SEARCH_RESULTS_LIMIT}")
    # run query
    query_str = "\n".join(query)
    result: Result = session.run(query_str, {"os_sha1_list": os_sha1_list, "search_expr": search_expr})
    for cursor in result:
        os_name, os_sha1, path, blob_sha1sum = cursor
        # path doesn't contain root, add it now
        path = f"/{path}"
        search_result = FSSearchResult(os_name, os_sha1, path, blob_sha1sum)
        yield search_result


def search_by_sha1(
    session: Union[Session, Transaction], os_sha1_list: Optional[List[str]], search_expr: str
) -> Iterator[FSSearchResult]:
    query = ["MATCH (o:Commit)-[:OWNS_FILESYSTEM]->(root:Tree)"]
    # filter OS if needed
    if os_sha1_list:
        # list is not None and not empty
        query.append("WHERE o.sha1sum IN $os_sha1_list")
    query.append("WITH o, root")
    # search filename
    query.append("MATCH path = (root)-[:HAS_CHILD_BLOB|HAS_CHILD_TREE*]->(b:Blob)")
    query.append("WITH relationships(path) as r_path, o")
    query.append("WHERE b.sha1sum = $search_expr")
    query.append("RETURN o.name, o.sha1sum, apoc.text.join([r IN r_path | r.name], '/'), endNode(last(r_path)).sha1sum")
    # add limit
    query.append(f"LIMIT {SEARCH_RESULTS_LIMIT}")
    # run query
    query_str = "\n".join(query)
    result: Result = session.run(query_str, {"os_sha1_list": os_sha1_list, "search_expr": search_expr})
    for cursor in result:
        os_name, os_sha1, path, blob_sha1sum = cursor
        # path doesn't contain root, add it now
        path = f"/{path}"
        search_result = FSSearchResult(os_name, os_sha1, path, blob_sha1sum)
        yield search_result
