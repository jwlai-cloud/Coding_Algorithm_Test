# To find the missing value for a known range

# if the range is known as a series consecutive integer, there is a quick way to find which one is missing

def solution(inp: list):
    num = len(inp)
    # In case input is empty
    if num > 0:
        actual_sum = sum(inp)
        # The max(last) number will be
        min_number = min(inp)
        max_number = min_number + num
        # to get the expect sum, since it is supposed to be consecutive,
        # we can use method like x*(x+1)/2, Gaussian way
        expected_sum = (num + 1) * (min_number + max_number) / 2
        missing = int(expected_sum - actual_sum)
    else:
        missing = None

    return missing

if __name__ == '__main__':
    print(solution([2, 3, 1, 5]))
    print(solution([2, 3, 1, 4, 6, 5, 8, 7, 9]))
    print(solution([]))

