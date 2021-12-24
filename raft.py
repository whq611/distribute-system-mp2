import time
import sys
import json
import random
import threading

my_id = int(sys.argv[1])
total_ids = int(sys.argv[2])

RAND_MIN = 15
RAND_MAX = 30
TIME_SCALE = 1
HEARTBEAT_INTERVAL = 1


class StateManager:
    def __init__(self, index, total_server_ids):
        self.lock = threading.Lock()
        self.id = index
        self.other_server_ids = []
        self.leader_id = None
        self.state = "FOLLOWER"
        self.current_term = 1
        self.votes_count = 0
        self.voted = False
        self.commit_index = 0
        self.log = []
        self.log.append({self.current_term, None})
        self.last_RPC_time = None
        self.last_heartbeat_time = None
        self.election_timeout = random.uniform(RAND_MIN, RAND_MAX)
        for i in range(total_server_ids):
            if i != index:
                self.other_server_ids.append(i)

    def send_t(self):
        while True:
            if (
                self.last_RPC_time == None
                or time.time() * TIME_SCALE - self.last_RPC_time > self.election_timeout
            ) and self.state != "LEADER":
                self.start_election()
                self.send_vote_requests()
            elif (
                self.last_heartbeat_time == None
                or self.last_heartbeat_time - time.time() * TIME_SCALE
                > HEARTBEAT_INTERVAL
            ) and self.state == "LEADER":
                self.heartbeat_t()
            time.sleep(0.1)

    def start_election(self):
        self.lock.acquire()
        self.votes_count += 1
        self.voted = True
        self.current_term += 1
        self.leader_id = None
        self.state = "CANDIDATE"
        self.last_RPC_time = time.time() * TIME_SCALE
        self.lock.release()

    def send_vote_requests(self):
        print('STATE state="CANDIDATE"', flush=True)
        print("STATE leader=null", flush=True)
        print("STATE term=" + str(self.current_term), flush=True)
        for i in self.other_server_ids:
            print(
                f"SEND {i} RequestVotes {str(self.current_term)}", flush=True,
            )

    def send_vote_response(self, term, source):
        print(
            f"SEND {source} RequestVotesResponse {term}", flush=True,
        )
        print('STATE state="CANDIDATE"', flush=True)
        print("STATE leader=null", flush=True)
        print(f"STATE term={term}", flush=True)

    def leader_selection(self):
        self.lock.acquire()
        self.votes_count += 1
        self.lock.release()
        if self.votes_count > (len(self.other_server_ids) + 1) / 2:
            self.lock.acquire()
            self.leader_id = str(self.id)
            self.state = "LEADER"
            self.votes_count = 0
            self.lock.release()
        print('STATE state="LEADER"', flush=True)
        print(f'STATE leader="{self.id}"', flush=True)

    def be_follower(self, source, term):
        print("STATE leader=null", flush=True)
        self.lock.acquire()
        self.leader_id = str(source)
        self.state = "FOLLOWER"
        self.current_term = int(term)
        self.lock.release()
        print(f"STATE term={term}")
        print('STATE state="FOLLOWER"', flush=True)
        print(f'STATE leader="{source}"', flush=True)

    def send_append_entries_response(self, source, term):
        print(
            f"SEND {source} AppendEntriesResponse {term} true", flush=True,
        )

    def receive_t(self):
        for line in sys.stdin:
            _, source, req, args = line.strip().split(" ", 3)
            args_l = args.split(" ")
            term = args_l[0]
            if int(term) >= self.current_term:
                if req == "RequestVotes":
                    if self.voted == False:
                        self.lock.acquire()
                        self.voted = True
                        self.last_RPC_time = time.time() * TIME_SCALE
                        self.state = "CANDIDATE"
                        self.leader_id = None
                        self.current_term = int(term)
                        self.lock.release()
                        self.send_vote_response(term, source)
                elif req == "RequestVotesResponse":
                    self.leader_selection()

                elif req == "AppendEntries":
                    if self.state == "CANDIDATE" or int(term) > self.current_term:
                        self.be_follower(source, term)
                    self.lock.acquire()
                    self.last_RPC_time = time.time() * TIME_SCALE
                    self.votes_count = 0
                    self.voted = False
                    self.lock.release()
                    if len(args_l) == 2:
                        pass
                    elif len(args_l) == 3:
                        pass
                    self.send_append_entries_response(source, term)
                elif req == "AppendEntriesResponse":
                    if args_l[1] == "true":
                        pass

    def heartbeat_t(self):
        while True:
            if self.leader_id == str(self.id):
                self.lock.acquire()
                self.last_heartbeat_time = time.time() * TIME_SCALE
                self.last_RPC_time = time.time() * TIME_SCALE
                self.lock.release()
                for i in self.other_server_ids:
                    print(
                        f"SEND {i} AppendEntries {self.current_term}", flush=True,
                    )
                time.sleep(0.1)

    def run(self):
        t1 = threading.Thread(target=self.receive_t)
        t2 = threading.Thread(target=self.send_t)
        t1.start()
        t2.start()


def main():
    global my_id, total_ids
    my_server = StateManager(my_id, total_ids)
    my_server.run()


if __name__ == "__main__":
    main()
