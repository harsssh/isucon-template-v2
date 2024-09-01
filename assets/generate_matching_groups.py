#!/usr/bin/env python3
import re
import sys


# echo を想定した実装
# group は考慮しない
def extract_route_from_line(line):
    """
    ソースコードの行から、ルーティングのパスを抽出する
    """
    methods = ['GET', 'POST', 'PUT', 'DELETE']
    # ルーティングに関する行か?
    if not any(f'.{method}(' in line for method in methods):
        return None

    # 第一引数を抽出
    # ダブルクォートの中身を抽出でよい?
    # e.GET("/api/users/:user_id", handler)
    route_match = re.search(r'".*"', line)
    if route_match is None:
        return None

    route = route_match.group(0)
    route = route.strip('"')

    return route


def extract_routes(input_stream):
    routes = []
    for line in input_stream:
        line = line.strip()
        if not line:
            continue

        route = extract_route_from_line(line)
        if route is not None:
            routes.append(route)

    return routes


def create_route_regex_list(routes):
    route_regex_list = []
    for i, route in enumerate(routes):
        if not contain_params(route):
            continue

        route_regex = replace_params(route)

        matching_routes = [(j, r) for j, r in enumerate(routes) if re.match(route_regex, r)]
        if len(matching_routes) > 1:
            # /api/users/:user_id と /api/users/:user_id/friends などは区別できない
            # 後者のパターンを先にマッチさせる
            for _, preferred_route in filter(lambda t: t[0] != i, matching_routes):
                route_regex_list.append(f'^{preferred_route}$')

        route_regex_list.append(route_regex)

    return route_regex_list


def replace_params(route):
    return '^' + re.sub(r'/:[^/]+', '/[^/]+', route) + '$'


def contain_params(route):
    """
    ルーティングのパスにパラメータが含まれているか
    """
    return ':' in route


def print_as_yaml_list(route_regex_list):
    """
    alp の matching_groups 用の文字列を出力する
    """
    print('matching_groups:')
    for route_regex in route_regex_list:
        print(f'  - {route_regex}')


def main():
    """
    ソースコードを解析して、alp の matching_groups 用の文字列を出力する
    """
    if len(sys.argv) == 2:
        filename = sys.argv[1]
        with open(filename, 'r') as f:
            routes = extract_routes(f)
    elif len(sys.argv) == 1:
        routes = extract_routes(sys.stdin)
    else:
        print('Usage: python3 generate_matching_groups.py [filename]')
        sys.exit(1)

    route_regex_list = create_route_regex_list(routes)
    print_as_yaml_list(route_regex_list)


if __name__ == '__main__':
    main()
