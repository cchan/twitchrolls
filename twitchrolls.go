package main

import (
  "sort"
  "net/http"
  "time"
  "strings"
  "math/rand"
  "github.com/valyala/fasthttp"
  "github.com/json-iterator/go"
  "fmt"
  "io/ioutil"
  "strconv"
  "bytes"
  "net/url"
  "errors"
)

var json = jsoniter.ConfigCompatibleWithStandardLibrary

type APIPagination struct {
  Cursor string
}
type StreamInfoFake struct {
  Viewer_count int
  Game_id string
  User_name string
  Thumbnail_url string
}
type StreamInfo struct {
  Viewer_count int
  Game_id int
  User_name string
  Thumbnail_url string
}
type StreamAPIResult struct {
  Data []StreamInfo
  Pagination APIPagination
}
type StreamAPIResultFake struct {
  Data []StreamInfoFake
  Pagination APIPagination
}
type GameInfo struct {
  Id int           `json:",string"`
}
type GameAPIResult struct {
  Data []GameInfo
}

const ITERATIONS int = 100 // number of queries (100 each) to Helix. Rate limit is 120 per minute, so we can refresh this every 30 sec without issues.
const REFRESHTIME time.Duration = 70 * time.Second

const CLIENT_ID string = "gp762nuuoqcoxypju8c569th9wz7q5"
const OAUTH string = "Bearer fob6uh9x6z1jyv6pfrjpv0bswnaz9e"

var sorted_data []StreamInfo
var client http.Client

func apicall(path string) ([]byte, error) {
  url := "https://api.twitch.tv/helix" + path
  req, err := http.NewRequest("GET", url, nil)
  if err != nil { return []byte{}, err }
  req.Header.Add("Client-ID", CLIENT_ID)
  req.Header.Add("Authorization", OAUTH)
  
  resp, err := client.Do(req)
  if err != nil { return []byte{}, err }
  if resp.StatusCode != 200 { return []byte{}, errors.New("Non-200 response") }
  defer resp.Body.Close()
  
  return ioutil.ReadAll(resp.Body)
}

func streamapicall(path string) (StreamAPIResult, error) {
  resultbytes, err := apicall(path)
  var result StreamAPIResult
  var resultFake StreamAPIResultFake
  if err != nil { return result, err }
  err = json.Unmarshal(resultbytes, &resultFake)
  if err != nil { return result, err }
  result.Pagination = resultFake.Pagination
  for i := range resultFake.Data {
    x, err := strconv.Atoi(resultFake.Data[i].Game_id)
    if err != nil {
      x = -2
    }
    result.Data = append(result.Data, StreamInfo{
      Viewer_count: resultFake.Data[i].Viewer_count,
      Game_id: x,
      User_name: resultFake.Data[i].User_name,
      Thumbnail_url: resultFake.Data[i].Thumbnail_url,
    })
  }
  return result, nil
}
func gameapicall(path string) (GameAPIResult, error) {
  resultbytes, err := apicall(path)
  var result GameAPIResult
  if err != nil { return result, err }
  err = json.Unmarshal(resultbytes, &result)
  if err != nil { return result, err }
  return result, nil
}

func get_sorted_data() []StreamInfo {
    cur := ""

    var total_data []StreamInfo
    for i := 0; i < ITERATIONS; i++ {
        result, err := streamapicall("/streams?first=100&language=en" + cur)
        if err != nil { fmt.Println(err); break }
        total_data = append(total_data, result.Data...)
        cur = "&after=" + result.Pagination.Cursor
    }

    sort.Slice(total_data, func(i, j int) bool {
      return total_data[i].Viewer_count < total_data[j].Viewer_count
    })
    
    fmt.Println("sorted")

    return total_data
}

func get_sorted_data_loop() {
  for {
    sorted_data = get_sorted_data()
    time.Sleep(REFRESHTIME)
  }
}

var game_ids map[string]int = make(map[string]int)
func get_game_id(gamename string) int {
    gamename = strings.ToLower(strings.Trim(gamename, " \t\n"))
    if game_id, ok := game_ids[gamename]; ok {
      return game_id
    }
    result, err := gameapicall("/games?name=" + url.QueryEscape(gamename))
    var game_id int
    if err != nil {
      game_id = -1
    } else if len(result.Data) > 0 {
      game_id = result.Data[0].Id
    } else {
      game_id = -1
    }
    game_ids[gamename] = game_id
    fmt.Printf("%s %d\n", gamename, game_id)
    return game_id
}

func get_winners(nwin int, thresh int, gamename string) string {
    if nwin < 0 { nwin = 0 }
    if nwin > len(sorted_data) { nwin = len(sorted_data) }
    
    my_sorted_data := sorted_data // In case the get_sorted_data thread decides to change it, we still keep a reference to the same slice
    lastExclusive := sort.Search(len(my_sorted_data), func(i int) bool {
        return my_sorted_data[i].Viewer_count > thresh
    })
    small_streams := my_sorted_data[:lastExclusive]
    starttime := time.Now()
    
    var filtered_streams []StreamInfo
    if gamename == "all" {
      filtered_streams = make([]StreamInfo, len(small_streams))
      copy(filtered_streams, small_streams)
    } else {
      game_id := get_game_id(gamename)
      for _, stream := range small_streams {
        if stream.Game_id != 0 && stream.Game_id == game_id {
          filtered_streams = append(filtered_streams, stream)
        }
      }
    }
    fmt.Println(time.Since(starttime).Microseconds())
    
    var winners []StreamInfo
    if nwin >= len(filtered_streams) {
      winners = filtered_streams
    } else {
      for i := 0; i < nwin; i++ {
        j := i + rand.Intn(len(filtered_streams) - i)
        filtered_streams[i], filtered_streams[j] = filtered_streams[j], filtered_streams[i]
      }
      winners = filtered_streams[:nwin]
    }
    
    cards := ""
    for _, winner := range winners {
        user := winner.User_name
        url := winner.Thumbnail_url
        url = strings.ReplaceAll(url, "{width}", "400")
        url = strings.ReplaceAll(url, "{height}", "300")
        cards += fmt.Sprintf("<a target='_blank' class='card' href='https://twitch.tv/%s'><img src='%s'><div>%s</div></a>", user, url, user)
    }
    if cards == "" {
        cards = "none found :("
    }
    return cards
}


func handler(ctx *fasthttp.RequestCtx) {
  p := ctx.Path()
  fmt.Println(string(p))
  if string(p) == "/" {
    ctx.Response.Header.Set("Cache-Control", "public, max-age=7200")
    ctx.SendFile("twitchrolls.html")
    return
  }
  s1 := bytes.Index(p, []byte("/"))
  if s1 == -1 { ctx.Response.SetBodyString("Invalid input"); return }
  s2 := bytes.Index(p[s1+1:], []byte("/"))
  if s2 == -1 { ctx.Response.SetBodyString("Invalid input"); return }
  s3 := bytes.Index(p[s1+1+s2+1:], []byte("/"))
  if s3 == -1 { ctx.Response.SetBodyString("Invalid input"); return }
  s4 := bytes.Index(p[s1+1+s2+1+s3+1:], []byte("/"))
  if s4 == -1 { ctx.Response.SetBodyString("Invalid input"); return }
  s2 += s1 + 1
  s3 += s2 + 1
  s4 += s3 + 1
  nwin, err := strconv.Atoi(string(p[s2+1:s3]))
  if err != nil {
    ctx.Response.SetBodyString("Invalid input")
    return
  }
  thresh, err := strconv.Atoi(string(p[s3+1:s4]))
  if err != nil {
    ctx.Response.SetBodyString("Invalid input")
    return
  }
  gamename := string(p[s4+1:])
  fmt.Printf("%s get3 {%d} {%d} {%s}\n", time.Now().String(), nwin, thresh, gamename)
  ctx.Response.SetBodyString(get_winners(nwin, thresh, gamename))
}
func main() {
  go get_sorted_data_loop()
  fasthttp.ListenAndServe(":5000", handler)
}
